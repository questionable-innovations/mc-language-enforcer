package io.github.questionableinnovations.langenforcer.voice;

import de.maxhenkel.voicechat.api.ForgeVoicechatPlugin;
import de.maxhenkel.voicechat.api.VoicechatConnection;
import de.maxhenkel.voicechat.api.VoicechatPlugin;
import de.maxhenkel.voicechat.api.VoicechatServerApi;
import de.maxhenkel.voicechat.api.events.EventRegistration;
import de.maxhenkel.voicechat.api.events.MicrophonePacketEvent;
import de.maxhenkel.voicechat.api.events.PlayerDisconnectedEvent;
import de.maxhenkel.voicechat.api.events.VoicechatServerStartedEvent;
import de.maxhenkel.voicechat.api.events.VoicechatServerStoppedEvent;
import io.github.questionableinnovations.langenforcer.Config;
import io.github.questionableinnovations.langenforcer.LangEnforcer;
import io.github.questionableinnovations.langenforcer.PlayerRules;
import io.github.questionableinnovations.langenforcer.Punisher;
import io.github.questionableinnovations.langenforcer.rules.ActiveRules;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraftforge.server.ServerLifecycleHooks;

import java.time.Duration;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

/** Listens to every microphone packet SVC relays. Never cancels or alters audio: punishment is damage only. */
@ForgeVoicechatPlugin
public final class VoicePlugin implements VoicechatPlugin {
    private static final int MAX_IN_FLIGHT_PER_PLAYER = 3;

    private final Map<UUID, Speaker> speakers = new ConcurrentHashMap<>();
    private final Map<UUID, AtomicInteger> inFlight = new ConcurrentHashMap<>();
    private volatile VoicechatServerApi api;
    private ScheduledExecutorService silenceWatch;

    @Override
    public String getPluginId() {
        return LangEnforcer.MODID;
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
        LangEnforcer.LOG.info("Listening to Simple Voice Chat; judging speech at {}", Config.SIDECAR_URL.get());
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
        ActiveRules rules = PlayerRules.get(id);
        if (!rules.isActive()) {
            Speaker idle = speakers.get(id);
            if (idle != null) idle.discard();
            return;
        }
        Speaker speaker = speakers.computeIfAbsent(id, u -> new Speaker(u, api.createDecoder()));
        speaker.onPacket(event.getPacket().getOpusEncodedData(), Config.MAX_SECONDS.get(), Config.MIN_SECONDS.get(), this::judge);
    }

    private void flushSilent() {
        try {
            long silence = TimeUnit.MILLISECONDS.toNanos(Config.END_SILENCE_MS.get());
            double min = Config.MIN_SECONDS.get();
            for (Speaker s : speakers.values()) s.flushIfSilent(silence, min, this::judge);
        } catch (RuntimeException e) {
            LangEnforcer.LOG.error("Silence watcher failed", e);
        }
    }

    private void judge(Speaker.Utterance u) {
        MinecraftServer server = ServerLifecycleHooks.getCurrentServer();
        if (server == null) return;
        AtomicInteger busy = inFlight.computeIfAbsent(u.player(), k -> new AtomicInteger());
        if (busy.incrementAndGet() > MAX_IN_FLIGHT_PER_PLAYER) {
            busy.decrementAndGet();
            return; // sidecar is behind; skipping beats queueing stale punishments
        }
        ActiveRules rules = PlayerRules.get(u.player());
        ServerPlayer named = server.getPlayerList().getPlayer(u.player());
        String name = named == null ? u.player().toString() : named.getGameProfile().getName();
        LangEnforcer.judge().judge(Config.SIDECAR_URL.get(), Config.SIDECAR_TOKEN.get(), Duration.ofSeconds(Config.SIDECAR_TIMEOUT_SECONDS.get()),
                        u.pcm16k(), rules, name)
                .whenComplete((v, e) -> busy.decrementAndGet())
                .thenAccept(opt -> opt.ifPresent(verdict -> {
                    if (Config.LOG_VERDICTS.get()) {
                        LangEnforcer.LOG.info("{} {}s [{}] -> {} {} severity={} ({}ms){}", name, String.format("%.1f", u.seconds()),
                                rules.toQuery(), verdict.violation() ? "VIOLATION" : "ok", verdict.rule() == null ? verdict.language() : verdict.rule(),
                                String.format("%.2f", verdict.severity()), verdict.ms(),
                                verdict.offending().isEmpty() ? "" : " " + verdict.offending());
                    }
                    if (!verdict.violation()) return;
                    server.execute(() -> {
                        ServerPlayer player = server.getPlayerList().getPlayer(u.player());
                        if (player != null) Punisher.apply(player, verdict, rules);
                    });
                }));
    }

    private void dropSpeaker(UUID id) {
        Speaker s = speakers.remove(id);
        if (s != null) s.close();
        inFlight.remove(id);
    }
}
