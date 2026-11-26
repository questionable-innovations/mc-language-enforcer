package io.github.questionableinnovations.langenforcer.rules;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.text.Normalizer;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;

/** Whisper's languages and every name an anvil-renamed banner may use for them. */
public final class Languages {
    public record Language(String code, String name, String nativeName) {
        public String display() {
            return name.equals(nativeName) ? name : name + " (" + nativeName + ")";
        }
    }

    private final Map<String, Language> byCode = new HashMap<>();
    private final Map<String, String> codeByName = new HashMap<>();

    public static Languages load() {
        try (InputStream in = Languages.class.getResourceAsStream("/langenforcer/languages.json")) {
            if (in == null) throw new IllegalStateException("languages.json missing from jar");
            return parse(JsonParser.parseReader(new InputStreamReader(in, StandardCharsets.UTF_8)).getAsJsonArray());
        } catch (java.io.IOException e) {
            throw new IllegalStateException(e);
        }
    }

    static Languages parse(JsonArray array) {
        Languages l = new Languages();
        for (JsonElement e : array) {
            JsonObject o = e.getAsJsonObject();
            Language lang = new Language(o.get("code").getAsString(), o.get("name").getAsString(), o.get("native").getAsString());
            l.byCode.put(lang.code(), lang);
            l.codeByName.put(normalize(lang.code()), lang.code());
            for (JsonElement n : o.getAsJsonArray("names")) {
                l.codeByName.putIfAbsent(normalize(n.getAsString()), lang.code());
            }
        }
        return l;
    }

    /** Matches a custom item name against language names, case/accent/width-insensitively. Codes need 2+ letters. */
    public Optional<String> codeForName(String name) {
        String key = normalize(name);
        return key.length() < 2 ? Optional.empty() : Optional.ofNullable(codeByName.get(key));
    }

    public Optional<Language> byCode(String code) {
        return Optional.ofNullable(byCode.get(code));
    }

    static String normalize(String s) {
        String n = Normalizer.normalize(s.strip(), Normalizer.Form.NFKD).replaceAll("\\p{M}", "");
        return n.toLowerCase(Locale.ROOT);
    }
}
