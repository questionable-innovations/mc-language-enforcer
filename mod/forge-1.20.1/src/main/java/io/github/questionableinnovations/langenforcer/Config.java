package io.github.questionableinnovations.langenforcer;

import io.github.questionableinnovations.langenforcer.core.Settings;
import net.minecraftforge.common.ForgeConfigSpec;

import java.util.List;

/** config/langenforcer-common.toml. Keep keys and defaults in step with the other loaders' Config. */
public final class Config {
    public static final ForgeConfigSpec SPEC;
    public static final Settings SETTINGS;

    static {
        ForgeConfigSpec.Builder b = new ForgeConfigSpec.Builder();

        b.comment("The speech-judging sidecar (docker image ghcr.io/questionable-innovations/mc-language-enforcer-sidecar)").push("sidecar");
        var url = b.define("url", "http://127.0.0.1:7860");
        var token = b.comment("Shared secret, must match the sidecar's LE_TOKEN. Empty = none.").define("token", "");
        var timeout = b.defineInRange("timeoutSeconds", 10, 1, 60);
        b.pop();

        b.comment("Damage ignores armour and armour enchantments. It scales with how sure the judge is.").push("damage");
        var minDamage = b.comment("Damage at the lowest confidence that still counts (2 = one heart)").defineInRange("min", 1.0, 0.0, 100.0);
        var maxDamage = b.comment("Damage when the judge is certain").defineInRange("max", 5.0, 0.0, 100.0);
        var lethal = b.comment("If false, speaking never takes the last half heart").define("lethal", true);
        b.pop();

        b.push("speech");
        var minSeconds = b.comment("Shorter bursts (\"ok\", \"gg\", names) are never judged").defineInRange("minSeconds", 0.8, 0.2, 10.0);
        var maxSeconds = b.comment("Longer speech is judged in chunks of this length, each can hurt").defineInRange("maxSeconds", 8.0, 2.0, 30.0);
        var endSilence = b.comment("Fallback end-of-speech detection if SVC's stop packet is lost").defineInRange("endSilenceMs", 500, 100, 5000);
        b.pop();

        b.push("rules");
        ForgeConfigSpec.ConfigValue<List<? extends String>> global = b.comment("Whisper language codes every player is held to, flag or not (e.g. [\"zh\"])")
                .defineListAllowEmpty(List.of("globalLanguages"), List::of, o -> o instanceof String);
        ForgeConfigSpec.ConfigValue<List<? extends String>> flags = b.comment(
                        "Loom designs that count as a language's flag: 'code = base | colour pattern, ...' (exact match).",
                        "Any banner renamed to a language name in an anvil also counts.")
                .defineListAllowEmpty(List.of("flags"), () -> Settings.DEFAULT_FLAGS, o -> o instanceof String);
        var rockWords = b.comment("Carry anything named \"Rock\": you may only use the N most common English words")
                .defineInRange("rockWords", 500, 10, 100000);
        b.pop();

        b.push("debug");
        var logVerdicts = b.comment("Log every judged utterance (player, rule, severity) to the server log").define("logVerdicts", true);
        b.pop();

        SPEC = b.build();
        SETTINGS = new Settings() {
            public String sidecarUrl() { return url.get(); }
            public String sidecarToken() { return token.get(); }
            public int sidecarTimeoutSeconds() { return timeout.get(); }
            public double minDamage() { return minDamage.get(); }
            public double maxDamage() { return maxDamage.get(); }
            public boolean lethal() { return lethal.get(); }
            public double minSeconds() { return minSeconds.get(); }
            public double maxSeconds() { return maxSeconds.get(); }
            public int endSilenceMs() { return endSilence.get(); }
            public List<? extends String> globalLanguages() { return global.get(); }
            public List<? extends String> flags() { return flags.get(); }
            public int rockWords() { return rockWords.get(); }
            public boolean logVerdicts() { return logVerdicts.get(); }
        };
    }

    private Config() {
    }
}
