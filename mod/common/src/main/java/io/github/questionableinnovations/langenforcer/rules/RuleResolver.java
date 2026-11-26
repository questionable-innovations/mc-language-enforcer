package io.github.questionableinnovations.langenforcer.rules;

import java.util.Collection;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

/** Turns what a player carries into the rules they are held to. Minecraft-free so it can be unit tested. */
public final class RuleResolver {
    /**
     * One inventory stack, reduced to what matters.
     *
     * @param customName anvil name, or null
     * @param bannerBase dye name of the banner's base colour (banner or banner-decorated shield), or null if neither
     * @param layers     the banner's pattern layers (empty for non-banners)
     */
    public record Carried(String customName, String bannerBase, List<FlagDesign.Layer> layers) {
        public boolean isBanner() {
            return bannerBase != null;
        }
    }

    private final Languages languages;
    private final List<FlagDesign> designs;
    private final Set<String> global;
    private final int rockWords;

    public RuleResolver(Languages languages, List<FlagDesign> designs, Collection<String> globalLanguages, int rockWords) {
        this.languages = languages;
        this.designs = List.copyOf(designs);
        this.global = Set.copyOf(globalLanguages);
        this.rockWords = rockWords;
    }

    public ActiveRules resolve(Iterable<Carried> inventory) {
        Set<String> langs = new HashSet<>(global);
        boolean rock = false, mime = false, gadsby = false;
        for (Carried c : inventory) {
            if (c.customName() != null) {
                // Easter eggs work on any item: a cobblestone renamed "Rock" is the intended joke
                switch (c.customName().strip().toLowerCase(Locale.ROOT)) {
                    case "rock" -> { rock = true; continue; }
                    case "mime" -> { mime = true; continue; }
                    case "gadsby", "lipogram" -> { gadsby = true; continue; }
                    default -> { }
                }
                if (c.isBanner()) {
                    var code = languages.codeForName(c.customName());
                    if (code.isPresent()) {
                        langs.add(code.get());
                        continue;
                    }
                }
            }
            if (c.isBanner()) {
                for (FlagDesign d : designs) {
                    if (d.matches(c.bannerBase(), c.layers())) langs.add(d.language());
                }
            }
        }
        return new ActiveRules(langs, rock ? rockWords : 0, mime, gadsby);
    }
}
