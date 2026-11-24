package io.github.questionableinnovations.langenforcer;

import io.github.questionableinnovations.langenforcer.judge.Verdict;
import io.github.questionableinnovations.langenforcer.rules.ActiveRules;
import io.github.questionableinnovations.langenforcer.rules.FlagDesign;
import io.github.questionableinnovations.langenforcer.rules.FlagDesign.Layer;
import io.github.questionableinnovations.langenforcer.rules.Languages;
import io.github.questionableinnovations.langenforcer.rules.RuleResolver;
import io.github.questionableinnovations.langenforcer.rules.RuleResolver.Carried;
import io.github.questionableinnovations.langenforcer.voice.Downsampler;
import io.github.questionableinnovations.langenforcer.voice.ShortBuffer;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

import static org.junit.jupiter.api.Assertions.*;

class RulesTest {
    static final Languages LANGS = Languages.load();
    static final List<FlagDesign> DESIGNS = Config.DEFAULT_FLAGS.stream().map(FlagDesign::parse).collect(Collectors.toList());
    static final RuleResolver RESOLVER = new RuleResolver(LANGS, DESIGNS, List.of(), 500);
    static final List<Layer> CHINA = List.of(new Layer("yellow", "square_top_left"), new Layer("red", "triangles_top"),
            new Layer("red", "border"));

    static ActiveRules resolve(Carried... c) {
        return RESOLVER.resolve(List.of(c));
    }

    @Test
    void loomCraftedChinaFlagEnforcesMandarin() {
        assertEquals(Set.of("zh"), resolve(new Carried(null, "red", CHINA)).languages());
    }

    @Test
    void halfFinishedFlagDoesNothing() {
        assertFalse(resolve(new Carried(null, "red", CHINA.subList(0, 2))).isActive());
        assertFalse(resolve(new Carried(null, "white", CHINA)).isActive());
    }

    @Test
    void anvilRenamedBannerWorksForAnyLanguage() {
        assertEquals(Set.of("zh"), resolve(new Carried("中文", "white", List.of())).languages());
        assertEquals(Set.of("zh"), resolve(new Carried("  chinese ", "white", List.of())).languages());
        assertEquals(Set.of("ja"), resolve(new Carried("日本語", "white", List.of())).languages());
        assertEquals(Set.of("mi"), resolve(new Carried("Te Reo Maori", "white", List.of())).languages());
        assertEquals(Set.of("es"), resolve(new Carried("ESPANOL", "white", List.of())).languages());
    }

    @Test
    void renamedNonBannerIsNotAFlag() {
        assertFalse(resolve(new Carried("中文", null, List.of())).isActive());
    }

    @Test
    void flagsCombine() {
        assertEquals(Set.of("zh", "ja"), resolve(new Carried(null, "red", CHINA), new Carried(null, "white", List.of(new Layer("red", "circle")))).languages());
    }

    @Test
    void easterEggsWorkOnAnyItem() {
        ActiveRules rock = resolve(new Carried("Rock", null, List.of()));
        assertEquals(500, rock.rock());
        assertTrue(resolve(new Carried("mime", null, List.of())).mime());
        assertTrue(resolve(new Carried("Gadsby", null, List.of())).gadsby());
    }

    @Test
    void globalLanguagesApplyToEveryone() {
        RuleResolver global = new RuleResolver(LANGS, DESIGNS, List.of("zh"), 500);
        assertEquals(Set.of("zh"), global.resolve(List.of()).languages());
    }

    @Test
    void queryStringIsStable() {
        assertEquals("allow=ja%2Czh&rock=0&mime=false&gadsby=false", new ActiveRules(Set.of("zh", "ja"), 0, false, false).toQuery());
    }

    @Test
    void flagDesignParsingAcceptsNamespaces() {
        FlagDesign d = FlagDesign.parse("ja = white | red minecraft:circle");
        assertTrue(d.matches("white", List.of(new Layer("red", "circle"))));
        assertThrows(IllegalArgumentException.class, () -> FlagDesign.parse("nonsense"));
    }

    @Test
    void damageScalesWithSeverity() {
        assertEquals(1.0f, Verdict.damage(0, 1, 5));
        assertEquals(3.0f, Verdict.damage(0.5, 1, 5));
        assertEquals(5.0f, Verdict.damage(2, 1, 5));
    }

    @Test
    void verdictParses() {
        Verdict v = Verdict.parse("{\"violation\":true,\"severity\":0.8,\"rule\":\"rock\",\"language\":\"en\",\"p_allowed\":0.9,"
                + "\"transcript\":\"I need diamonds\",\"offending\":[\"diamonds\"],\"ms\":120}");
        assertTrue(v.violation());
        assertEquals("rock", v.rule());
        assertEquals(List.of("diamonds"), v.offending());
    }

    @Test
    void downsamplerKeepsSpeechBandAndRejectsAliasing() {
        assertTrue(outputRms(1000) > 0.6 * 10000 / Math.sqrt(2), "1 kHz should pass");
        assertTrue(outputRms(14000) < 0.05 * 10000, "14 kHz must not alias into the 16 kHz output");
    }

    /** RMS of a 10000-amplitude 48 kHz sine after downsampling to 16 kHz. */
    static double outputRms(double hz) {
        Downsampler ds = new Downsampler();
        ShortBuffer out = new ShortBuffer();
        for (int frame = 0; frame < 50; frame++) {
            short[] in = new short[960];
            for (int i = 0; i < 960; i++) {
                in[i] = (short) (10000 * Math.sin(2 * Math.PI * hz * (frame * 960 + i) / 48000.0));
            }
            ds.process(in, out);
        }
        assertEquals(50 * 320, out.size());
        double sum = 0;
        for (int i = 1000; i < out.size(); i++) sum += out.get(i) * (double) out.get(i);
        return Math.sqrt(sum / (out.size() - 1000));
    }
}
