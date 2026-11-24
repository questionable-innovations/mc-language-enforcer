package io.github.questionableinnovations.langenforcer.voice;

import de.maxhenkel.voicechat.api.opus.OpusDecoder;

import java.util.UUID;
import java.util.function.Consumer;

/**
 * One player's speech in progress. Opus frames are decoded and downsampled as they arrive; the utterance is
 * handed off when SVC's empty stop packet arrives, after a silence timeout, or when it gets too long.
 */
public final class Speaker {
    public static final int RATE = 16000;

    public record Utterance(UUID player, byte[] pcm16k, double seconds) {
    }

    private final UUID player;
    private final OpusDecoder decoder;
    private final Downsampler downsampler = new Downsampler();
    private final ShortBuffer buffer = new ShortBuffer();
    private volatile long lastPacketNanos;

    public Speaker(UUID player, OpusDecoder decoder) {
        this.player = player;
        this.decoder = decoder;
    }

    public synchronized void onPacket(byte[] opus, double maxSeconds, double minSeconds, Consumer<Utterance> sink) {
        lastPacketNanos = System.nanoTime();
        if (opus.length == 0) {
            flush(minSeconds, sink);
            return;
        }
        downsampler.process(decoder.decode(opus), buffer);
        if (buffer.size() >= maxSeconds * RATE) {
            // Long monologue: judge it in pieces so a rant costs more than one hit
            emit(sink);
        }
    }

    public synchronized void flushIfSilent(long silenceNanos, double minSeconds, Consumer<Utterance> sink) {
        if (buffer.size() > 0 && System.nanoTime() - lastPacketNanos > silenceNanos) flush(minSeconds, sink);
    }

    private void flush(double minSeconds, Consumer<Utterance> sink) {
        if (buffer.size() >= minSeconds * RATE) emit(sink);
        buffer.clear();
        downsampler.reset();
        decoder.resetState();
    }

    private void emit(Consumer<Utterance> sink) {
        sink.accept(new Utterance(player, buffer.toLittleEndianBytes(), buffer.size() / (double) RATE));
        buffer.clear();
    }

    public synchronized void discard() {
        buffer.clear();
        downsampler.reset();
    }

    public synchronized void close() {
        buffer.clear();
        if (!decoder.isClosed()) decoder.close();
    }
}
