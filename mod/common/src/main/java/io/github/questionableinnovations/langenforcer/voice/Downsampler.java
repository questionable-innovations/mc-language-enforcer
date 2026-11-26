package io.github.questionableinnovations.langenforcer.voice;

/**
 * 48 kHz to 16 kHz with a windowed-sinc low-pass (cutoff ~7 kHz), streaming across Opus frames.
 * Whisper wants 16 kHz; sending it also cuts sidecar traffic by two thirds.
 */
public final class Downsampler {
    private static final int FACTOR = 3;
    private static final float[] TAPS = design(31, 7000.0 / 48000.0);

    private final float[] history = new float[TAPS.length - 1];
    private int phase;

    private static float[] design(int n, double cutoff) {
        float[] h = new float[n];
        double sum = 0;
        int mid = n / 2;
        for (int i = 0; i < n; i++) {
            int k = i - mid;
            double sinc = k == 0 ? 2 * cutoff : Math.sin(2 * Math.PI * cutoff * k) / (Math.PI * k);
            double hamming = 0.54 - 0.46 * Math.cos(2 * Math.PI * i / (n - 1));
            h[i] = (float) (sinc * hamming);
            sum += h[i];
        }
        for (int i = 0; i < n; i++) h[i] /= (float) sum;
        return h;
    }

    /** Appends the 16 kHz samples produced by {@code in} to {@code out}; returns how many were written. */
    public int process(short[] in, ShortBuffer out) {
        int written = 0;
        int hl = history.length;
        float[] window = new float[hl + in.length];
        System.arraycopy(history, 0, window, 0, hl);
        for (int i = 0; i < in.length; i++) window[hl + i] = in[i];
        for (int i = 0; i < in.length; i++) {
            if (phase++ % FACTOR != 0) continue;
            float acc = 0;
            for (int t = 0; t < TAPS.length; t++) acc += TAPS[t] * window[i + t];
            out.add((short) Math.max(Short.MIN_VALUE, Math.min(Short.MAX_VALUE, Math.round(acc))));
            written++;
        }
        System.arraycopy(window, window.length - hl, history, 0, hl);
        return written;
    }

    public void reset() {
        java.util.Arrays.fill(history, 0);
        phase = 0;
    }
}
