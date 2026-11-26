package io.github.questionableinnovations.langenforcer.voice;

import de.maxhenkel.voicechat.api.VoicechatConnection;
import de.maxhenkel.voicechat.api.VoicechatPlugin;
import de.maxhenkel.voicechat.api.VoicechatServerApi;
import de.maxhenkel.voicechat.api.events.EventRegistration;
import de.maxhenkel.voicechat.api.events.MicrophonePacketEvent;
import de.maxhenkel.voicechat.api.events.PlayerDisconnectedEvent;
import de.maxhenkel.voicechat.api.events.VoicechatServerStartedEvent;
import de.maxhenkel.voicechat.api.events.VoicechatServerStoppedEvent;
import io.github.questionableinnovations.langenforcer.core.Enforcer;
import io.github.questionableinnovations.langenforcer.core.Settings;
import io.github.questionableinnovations.langenforcer.judge.Verdict;
import io.github.questionableinnovations.langenforcer.rules.ActiveRules;

import java.time.Duration;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Listens to every microphone packet SVC relays. Never cancels or alters audio: punishment is damage only.
 * Each loader subclasses this with SVC's plugin annotation and supplies the server-side hooks.
 */
public abstract class VoiceListener implements VoicechatPlugin {
    private static final int MAX_IN_FLIGHT_PER_PLAYER = 3;

    private final Map<UUID, Speaker> speakers = new ConcurrentHashMap<>();
    private final Map<UUID, AtomicInteger> inFlight = new ConcurrentHashMap<>();
    private volatile VoicechatServerApi api;
    private ScheduledExecutorService silenceWatch;

    /** Whether a game server is running to judge for. */
    protected abstract boolean serverRunning();

    /** The online player's name, or null. */
    protected abstract String playerName(UUID player);

    /** Hand a violation to the server thread for punishment. */
    protected abstract void punish(UUID player, Verdict verdict, ActiveRules rules);

    @Override
    public String getPluginId() {
        return Enforcer.MODID;
    }

    @Override
    public void registerEvents(EventRegistration registration) {
        registration.registerEvent(VoicechatServerStartedEvent.class, this::onStarted);
        registration.registerEvent(VoicechatServerStoppedEvent.class, e -> onStopped());
        registration.registerEvent(MicrophonePacketEvent.class, this::onMicrophone);
        registration.registerEvent(PlayerDisconnectedEvent.class, e -> dropSpeaker(e.getPlayerUuid()));
    }

    private void onStarted(VoicechatServerStartedEvent event) {
        api = event.getVoicechat();
        silenceWatch = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "langenforcer-silence");
            t.setDaemon(true);
            return t;
        });
        silenceWatch.scheduleAtFixedRate(this::flushSilent, 100, 100, TimeUnit.MILLISECONDS);
        Enforcer.LOG.info("Listening to Simple Voice Chat; judging speech at {}", Enforcer.settings().sidecarUrl());
    }

    private void onStopped() {
        if (silenceWatch != null) silenceWatch.shutdownNow();
        speakers.values().forEach(Speaker::close);
        speakers.clear();
    }

    private void onMicrophone(MicrophonePacketEvent event) {
        VoicechatConnection sender = event.getSenderConnection();
        if (sender == null || api == null) return;
        UUID id = sender.getPlayer().getUuid();
        ActiveRules rules = Enforcer.rules(id);
        if (!rules.isActive()) {
            Speaker idle = speakers.get(id);
            if (idle != null) idle.discard();
            return;
        }
        Settings s = Enforcer.settings();
        Speaker speaker = speakers.computeIfAbsent(id, u -> new Speaker(u, api.createDecoder()));
        speaker.onPacket(event.getPacket().getOpusEncodedData(), s.maxSeconds(), s.minSeconds(), this::judge);
    }

    private void flushSilent() {
        try {
            Settings s = Enforcer.settings();
            long silence = TimeUnit.MILLISECONDS.toNanos(s.endSilenceMs());
            double min = s.minSeconds();
            for (Speaker sp : speakers.values()) sp.flushIfSilent(silence, min, this::judge);
        } catch (RuntimeException e) {
            Enforcer.LOG.error("Silence watcher failed", e);
        }
    }

    private void judge(Speaker.Utterance u) {
        if (!serverRunning()) return;
        AtomicInteger busy = inFlight.computeIfAbsent(u.player(), k -> new AtomicInteger());
        if (busy.incrementAndGet() > MAX_IN_FLIGHT_PER_PLAYER) {
            busy.decrementAndGet();
            return; // sidecar is behind; skipping beats queueing stale punishments
        }
        Settings s = Enforcer.settings();
        ActiveRules rules = Enforcer.rules(u.player());
        String online = playerName(u.player());
        String name = online == null ? u.player().toString() : online;
        Enforcer.judge().judge(s.sidecarUrl(), s.sidecarToken(), Duration.ofSeconds(s.sidecarTimeoutSeconds()), u.pcm16k(), rules, name)
                .whenComplete((v, e) -> busy.decrementAndGet())
                .thenAccept(opt -> opt.ifPresent(verdict -> {
                    if (s.logVerdicts()) {
                        Enforcer.LOG.info("{} {}s [{}] -> {} {} severity={} ({}ms){}", name, String.format("%.1f", u.seconds()),
                                rules.toQuery(), verdict.violation() ? "VIOLATION" : "ok", verdict.rule() == null ? verdict.language() : verdict.rule(),
                                String.format("%.2f", verdict.severity()), verdict.ms(),
                                verdict.offending().isEmpty() ? "" : " " + verdict.offending());
                    }
                    if (verdict.violation()) punish(u.player(), verdict, rules);
                }));
    }

    private void dropSpeaker(UUID id) {
        Speaker sp = speakers.remove(id);
        if (sp != null) sp.close();
        inFlight.remove(id);
    }
}
