package io.github.questionableinnovations.langenforcer.judge;

import io.github.questionableinnovations.langenforcer.rules.ActiveRules;
import org.slf4j.Logger;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.Optional;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.atomic.AtomicLong;

/** Async HTTP client for the sidecar. Never blocks the game or the voice thread; fails open. */
public final class JudgeClient {
    private static final long WARN_EVERY_MS = 60_000;

    private final HttpClient http = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(3)).build();
    private final Logger log;
    private final AtomicLong lastWarn = new AtomicLong();

    public JudgeClient(Logger log) {
        this.log = log;
    }

    public CompletableFuture<Optional<Verdict>> judge(String baseUrl, String token, Duration timeout, byte[] pcm16k,
                                                      ActiveRules rules, String speaker) {
        HttpRequest.Builder req = HttpRequest.newBuilder(URI.create(stripSlash(baseUrl) + "/v1/judge?" + rules.toQuery()))
                .timeout(timeout)
                .header("Content-Type", "application/octet-stream")
                .header("X-Speaker", speaker)
                .POST(HttpRequest.BodyPublishers.ofByteArray(pcm16k));
        if (!token.isBlank()) req.header("Authorization", "Bearer " + token);
        return http.sendAsync(req.build(), HttpResponse.BodyHandlers.ofString())
                .thenApply(r -> {
                    if (r.statusCode() != 200) {
                        warn("sidecar answered HTTP " + r.statusCode() + ": " + r.body());
                        return Optional.<Verdict>empty();
                    }
                    return Optional.of(Verdict.parse(r.body()));
                })
                .exceptionally(e -> {
                    warn("sidecar unreachable at " + baseUrl + " (" + e.getClass().getSimpleName() + ": " + e.getMessage()
                            + "); speech is not being judged");
                    return Optional.empty();
                });
    }

    public CompletableFuture<String> health(String baseUrl) {
        HttpRequest req = HttpRequest.newBuilder(URI.create(stripSlash(baseUrl) + "/healthz")).timeout(Duration.ofSeconds(5)).GET().build();
        return http.sendAsync(req, HttpResponse.BodyHandlers.ofString()).thenApply(HttpResponse::body);
    }

    private void warn(String msg) {
        long now = System.currentTimeMillis();
        long last = lastWarn.get();
        if (now - last > WARN_EVERY_MS && lastWarn.compareAndSet(last, now)) log.warn(msg);
    }

    private static String stripSlash(String url) {
        return url.endsWith("/") ? url.substring(0, url.length() - 1) : url;
    }
}
