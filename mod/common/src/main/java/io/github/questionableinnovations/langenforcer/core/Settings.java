package io.github.questionableinnovations.langenforcer.core;

import java.util.List;

/** config/langenforcer-common.toml, read through whichever config system the loader has. */
public interface Settings {
    List<String> DEFAULT_FLAGS = List.of(
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

    String sidecarUrl();

    String sidecarToken();

    int sidecarTimeoutSeconds();

    double minDamage();

    double maxDamage();

    boolean lethal();

    double minSeconds();

    double maxSeconds();

    int endSilenceMs();

    List<? extends String> globalLanguages();

    List<? extends String> flags();

    int rockWords();

    boolean logVerdicts();
}
