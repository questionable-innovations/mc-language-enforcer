package io.github.questionableinnovations.langenforcer.voice;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.Arrays;

/** Growable PCM buffer. */
public final class ShortBuffer {
    private short[] data = new short[16000 * 4];
    private int size;

    public void add(short s) {
        if (size == data.length) data = Arrays.copyOf(data, data.length * 2);
        data[size++] = s;
    }

    public int size() {
        return size;
    }

    public void clear() {
        size = 0;
    }

    /** Little-endian signed 16-bit, the sidecar's wire format. */
    public byte[] toLittleEndianBytes() {
        ByteBuffer b = ByteBuffer.allocate(size * 2).order(ByteOrder.LITTLE_ENDIAN);
        for (int i = 0; i < size; i++) b.putShort(data[i]);
        return b.array();
    }

    public short get(int i) {
        return data[i];
    }
}
