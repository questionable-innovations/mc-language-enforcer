package io.github.questionableinnovations.langenforcer;

import net.minecraftforge.common.ForgeConfigSpec;

import java.util.List;

/** config/langenforcer-common.toml */
public final class Config {
    public static final ForgeConfigSpec SPEC;

    public static final ForgeConfigSpec.ConfigValue<String> SIDECAR_URL;
    public static final ForgeConfigSpec.ConfigValue<String> SIDECAR_TOKEN;
    public static final ForgeConfigSpec.IntValue SIDECAR_TIMEOUT_SECONDS;

    public static final ForgeConfigSpec.DoubleValue MIN_DAMAGE;
    public static final ForgeConfigSpec.DoubleValue MAX_DAMAGE;
    public static final ForgeConfigSpec.BooleanValue LETHAL;

    public static final ForgeConfigSpec.DoubleValue MIN_SECONDS;
    public static final ForgeConfigSpec.DoubleValue MAX_SECONDS;
    public static final ForgeConfigSpec.IntValue END_SILENCE_MS;

    public static final ForgeConfigSpec.ConfigValue<List<? extends String>> GLOBAL_LANGUAGES;
    public static final ForgeConfigSpec.ConfigValue<List<? extends String>> FLAGS;
    public static final ForgeConfigSpec.IntValue ROCK_WORDS;
    public static final ForgeConfigSpec.BooleanValue LOG_VERDICTS;

    public static final List<String> DEFAULT_FLAGS = List.of(
            // A star-like point in the top-left corner, like the flag's big star. No pattern item needed.
            "zh = red | yellow square_top_left, red triangles_top, red border",
            "ja = white | red circle",
            "fr = white | blue stripe_left, red stripe_right",
            "it = white | green stripe_left, red stripe_right",
            "de = red | black stripe_top, yellow stripe_bottom",
            "es = red | yellow stripe_middle",
            "ru = blue | white stripe_top, red stripe_bottom",
            "nl = white | red stripe_top, blue stripe_bottom",
            "pl = white | red half_horizontal_bottom",
            "id = white | red half_horizontal",
            "uk = blue | yellow half_horizontal_bottom",
            "sv = blue | yellow straight_cross");

    static {
        ForgeConfigSpec.Builder b = new ForgeConfigSpec.Builder();

        b.comment("The speech-judging sidecar (docker image ghcr.io/questionable-innovations/mc-language-enforcer-sidecar)").push("sidecar");
        SIDECAR_URL = b.define("url", "http://127.0.0.1:7860");
        SIDECAR_TOKEN = b.comment("Shared secret, must match the sidecar's LE_TOKEN. Empty = none.").define("token", "");
        SIDECAR_TIMEOUT_SECONDS = b.defineInRange("timeoutSeconds", 10, 1, 60);
        b.pop();

        b.comment("Damage ignores armour and armour enchantments. It scales with how sure the judge is.").push("damage");
        MIN_DAMAGE = b.comment("Damage at the lowest confidence that still counts (2 = one heart)").defineInRange("min", 1.0, 0.0, 100.0);
        MAX_DAMAGE = b.comment("Damage when the judge is certain").defineInRange("max", 5.0, 0.0, 100.0);
        LETHAL = b.comment("If false, speaking never takes the last half heart").define("lethal", true);
        b.pop();

        b.push("speech");
        MIN_SECONDS = b.comment("Shorter bursts (\"ok\", \"gg\", names) are never judged").defineInRange("minSeconds", 0.8, 0.2, 10.0);
        MAX_SECONDS = b.comment("Longer speech is judged in chunks of this length, each can hurt").defineInRange("maxSeconds", 8.0, 2.0, 30.0);
        END_SILENCE_MS = b.comment("Fallback end-of-speech detection if SVC's stop packet is lost").defineInRange("endSilenceMs", 500, 100, 5000);
        b.pop();

        b.push("rules");
        GLOBAL_LANGUAGES = b.comment("Whisper language codes every player is held to, flag or not (e.g. [\"zh\"])")
                .defineListAllowEmpty(List.of("globalLanguages"), List::of, o -> o instanceof String);
        FLAGS = b.comment("Loom designs that count as a language's flag: 'code = base | colour pattern, ...' (exact match).",
                        "Any banner renamed to a language name in an anvil also counts.")
                .defineListAllowEmpty(List.of("flags"), () -> DEFAULT_FLAGS, o -> o instanceof String);
        ROCK_WORDS = b.comment("Carry anything named \"Rock\": you may only use the N most common English words")
                .defineInRange("rockWords", 500, 10, 100000);
        b.pop();

        b.push("debug");
        LOG_VERDICTS = b.comment("Log every judged utterance (player, rule, severity) to the server log").define("logVerdicts", true);
        b.pop();

        SPEC = b.build();
    }

    private Config() {
    }
}
