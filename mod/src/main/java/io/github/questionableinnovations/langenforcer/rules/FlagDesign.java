package io.github.questionableinnovations.langenforcer.rules;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * A loom-craftable flag, parsed from config lines like
 * {@code zh = red | yellow square_top_left, red triangles_top, red border}.
 * Pattern names are banner pattern registry ids (minecraft namespace optional); colours are dye names.
 */
public record FlagDesign(String language, String base, List<Layer> layers) {
    public record Layer(String color, String pattern) {
    }

    public FlagDesign {
        layers = List.copyOf(layers);
    }

    public static FlagDesign parse(String line) {
        String[] langAndRest = line.split("=", 2);
        if (langAndRest.length != 2) throw new IllegalArgumentException("expected 'lang = base | layers': " + line);
        String lang = langAndRest[0].trim().toLowerCase(Locale.ROOT);
        String[] baseAndLayers = langAndRest[1].split("\\|", 2);
        String base = baseAndLayers[0].trim().toLowerCase(Locale.ROOT);
        List<Layer> layers = new ArrayList<>();
        if (baseAndLayers.length == 2 && !baseAndLayers[1].isBlank()) {
            for (String part : baseAndLayers[1].split(",")) {
                String[] cp = part.trim().split("\\s+", 2);
                if (cp.length != 2) throw new IllegalArgumentException("expected 'colour pattern': " + part);
                layers.add(new Layer(cp[0].toLowerCase(Locale.ROOT), stripNamespace(cp[1].toLowerCase(Locale.ROOT))));
            }
        }
        if (lang.isEmpty() || base.isEmpty()) throw new IllegalArgumentException("missing language or base: " + line);
        return new FlagDesign(lang, base, layers);
    }

    /** Exact match: same base colour and the same layers in the same order. */
    public boolean matches(String bannerBase, List<Layer> bannerLayers) {
        return base.equals(bannerBase) && layers.equals(bannerLayers);
    }

    static String stripNamespace(String id) {
        return id.startsWith("minecraft:") ? id.substring("minecraft:".length()) : id;
    }
}
