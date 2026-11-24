package io.github.questionableinnovations.langenforcer.judge;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.util.ArrayList;
import java.util.List;

/** The sidecar's answer for one utterance. */
public record Verdict(boolean violation, double severity, String rule, String language, String transcript,
                      List<String> offending, long ms) {

    public static Verdict parse(String json) {
        JsonObject o = JsonParser.parseString(json).getAsJsonObject();
        List<String> offending = new ArrayList<>();
        if (o.has("offending") && o.get("offending").isJsonArray()) {
            for (JsonElement e : o.getAsJsonArray("offending")) offending.add(e.getAsString());
        }
        return new Verdict(o.get("violation").getAsBoolean(), o.get("severity").getAsDouble(), str(o, "rule"),
                str(o, "language"), str(o, "transcript"), offending, o.has("ms") ? o.get("ms").getAsLong() : 0);
    }

    private static String str(JsonObject o, String k) {
        return o.has(k) && !o.get(k).isJsonNull() ? o.get(k).getAsString() : null;
    }

    /** Severity maps linearly onto [min, max]. */
    public static float damage(double severity, double min, double max) {
        double s = Math.max(0, Math.min(1, severity));
        return (float) (min + (max - min) * s);
    }
}
