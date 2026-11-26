package io.github.questionableinnovations.langenforcer.core;

import io.github.questionableinnovations.langenforcer.judge.JudgeClient;
import io.github.questionableinnovations.langenforcer.judge.Verdict;
import io.github.questionableinnovations.langenforcer.rules.ActiveRules;
import io.github.questionableinnovations.langenforcer.rules.FlagDesign;
import io.github.questionableinnovations.langenforcer.rules.Languages;
import io.github.questionableinnovations.langenforcer.rules.RuleResolver;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

/**
 * Everything that doesn't depend on Minecraft or the mod loader. Rules per online player are recomputed from their
 * inventory on the server thread and read from SVC's voice thread, which only ever sees this snapshot.
 */
public final class Enforcer {
    public static final String MODID = "langenforcer";
    public static final Logger LOG = LoggerFactory.getLogger("LanguageEnforcer");

    private static final JudgeClient JUDGE = new JudgeClient(LOG);
    private static final Map<UUID, ActiveRules> RULES = new ConcurrentHashMap<>();
    private static volatile Settings settings;
    private static Languages languages;
    private static volatile RuleResolver resolver;
    private static volatile List<?> resolverConfigKey;

    private Enforcer() {
    }

    public static void init(Settings s) {
        settings = s;
    }

    public static Settings settings() {
        return settings;
    }

    public static JudgeClient judge() {
        return JUDGE;
    }

    public static synchronized Languages languages() {
        if (languages == null) languages = Languages.load();
        return languages;
    }

    public static ActiveRules rules(UUID player) {
        return RULES.getOrDefault(player, ActiveRules.NONE);
    }

    public static ActiveRules refresh(UUID player, List<RuleResolver.Carried> carried) {
        ActiveRules r = resolver().resolve(carried);
        RULES.put(player, r);
        return r;
    }

    public static void forget(UUID player) {
        RULES.remove(player);
    }

    private static RuleResolver resolver() {
        // Rebuilt when the (hot-reloadable) config changes
        Settings s = settings;
        List<?> key = List.of(s.flags(), s.globalLanguages(), s.rockWords());
        if (resolver == null || !key.equals(resolverConfigKey)) {
            List<FlagDesign> designs = new ArrayList<>();
            for (String line : s.flags()) {
                try {
                    designs.add(FlagDesign.parse(line));
                } catch (IllegalArgumentException e) {
                    LOG.error("Ignoring bad flag design '{}': {}", line, e.getMessage());
                }
            }
            resolver = new RuleResolver(languages(), designs, List.copyOf(s.globalLanguages()), s.rockWords());
            resolverConfigKey = key;
        }
        return resolver;
    }

    public static Languages.Language describe(String code) {
        return languages().byCode(code).orElse(new Languages.Language(code, code, code));
    }

    /** Damage to deal for a verdict, or 0 for none. */
    public static float damage(UUID player, Verdict verdict, float health) {
        // Rules may have changed while the sidecar thought: dropping the flag mid-sentence gets you off the hook
        if (!verdict.violation() || !rules(player).isActive()) return 0;
        Settings s = settings;
        float amount = Verdict.damage(verdict.severity(), s.minDamage(), s.maxDamage());
        if (!s.lethal()) amount = Math.min(amount, health - 1.0f);
        return Math.max(0, amount);
    }

    /** Reply to {@code /langenforcer status}. */
    public static String status(String playerName, ActiveRules r) {
        if (!r.isActive()) return playerName + " speaks freely.";
        StringBuilder sb = new StringBuilder(playerName).append(" is held to: ");
        if (!r.languages().isEmpty()) {
            sb.append(r.languages().stream().map(c -> describe(c).display()).sorted().collect(Collectors.joining(", ")));
        }
        if (r.rock() > 0) sb.append(r.languages().isEmpty() ? "" : "; ").append("Rock (").append(r.rock()).append(" words)");
        if (r.gadsby()) sb.append("; no letter E");
        if (r.mime()) sb.append("; silence");
        return sb.toString();
    }

    /**
     * A death message: translation key, English fallback (clients usually lack this server-only mod's language file)
     * and the required languages for the {@code %s} after the victim, or null if the message has none.
     */
    public record DeathMessage(String key, String fallback, String required) {
    }

    public static DeathMessage deathMessage(Verdict verdict, ActiveRules rules) {
        String required = rules.languages().stream().map(c -> describe(c).name()).sorted().collect(Collectors.joining(" or "));
        return switch (verdict.rule() == null ? "language" : verdict.rule()) {
            case "rock" -> new DeathMessage("death.attack.langenforcer.rock", "%s used too many big words", null);
            case "gadsby" -> new DeathMessage("death.attack.langenforcer.gadsby", "%s said a word with an E in it", null);
            case "mime" -> new DeathMessage("death.attack.langenforcer.mime", "%s broke the vow of silence", null);
            default -> required.isEmpty()
                    ? new DeathMessage("death.attack.langenforcer.basic", "%s spoke out of turn", null)
                    : new DeathMessage("death.attack.langenforcer.language", "%s forgot to speak %s", required);
        };
    }
}
