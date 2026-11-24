package io.github.questionableinnovations.langenforcer.rules;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.Set;
import java.util.TreeSet;

/**
 * What a player is currently held to, derived from what they carry.
 *
 * @param languages Whisper codes the player must speak (union of carried flags)
 * @param rock      English vocabulary size for the "Rock" easter egg, 0 = off
 * @param mime      any speech hurts
 * @param gadsby    English words containing "e" hurt
 */
public record ActiveRules(Set<String> languages, int rock, boolean mime, boolean gadsby) {
    public static final ActiveRules NONE = new ActiveRules(Set.of(), 0, false, false);

    public ActiveRules {
        languages = Set.copyOf(new TreeSet<>(languages));
    }

    public boolean isActive() {
        return !languages.isEmpty() || rock > 0 || mime || gadsby;
    }

    /** Query string for the sidecar's /v1/judge endpoint. */
    public String toQuery() {
        return "allow=" + URLEncoder.encode(String.join(",", new TreeSet<>(languages)), StandardCharsets.UTF_8)
                + "&rock=" + rock + "&mime=" + mime + "&gadsby=" + gadsby;
    }
}
