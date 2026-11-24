"""HTTP API the Minecraft mod calls: POST raw 16 kHz mono s16le PCM, get a verdict back."""
from __future__ import annotations

import hmac
import logging
import os
import time
from contextlib import asynccontextmanager
from dataclasses import asdict

import numpy as np
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool

from .engine import SAMPLE_RATE, Engine
from .rules import Rules, Thresholds, judge

log = logging.getLogger("langenforcer")
MAX_SECONDS = 30


def env_float(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


def create_app(engine: Engine | None = None) -> FastAPI:
    token = os.environ.get("LE_TOKEN", "")
    log_transcripts = os.environ.get("LE_LOG_TRANSCRIPTS", "false").lower() in ("1", "true", "yes")
    th = Thresholds(tau=env_float("LE_TAU", Thresholds.tau), min_lp=env_float("LE_MIN_LP", Thresholds.min_lp))
    state = {"engine": engine}

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if state["engine"] is None:
            state["engine"] = Engine(
                os.environ.get("LE_MODEL", "auto"), os.environ.get("LE_DEVICE", "auto"),
                os.environ.get("LE_COMPUTE_TYPE", "auto"), int(os.environ.get("LE_CPU_THREADS", "4")),
                int(os.environ.get("LE_WORKERS", "2")), os.environ.get("LE_MODEL_DIR") or None)
            state["engine"].warm_up()
        yield

    app = FastAPI(title="Language Enforcer sidecar", lifespan=lifespan)

    @app.get("/healthz")
    def health() -> dict:
        e = state["engine"]
        return {"ok": e is not None, "model": e and e.model_name, "device": e and e.device,
                "compute_type": e and e.compute_type}

    @app.post("/v1/judge")
    async def judge_endpoint(
        request: Request,
        allow: str = Query("", description="comma-separated Whisper language codes, e.g. zh"),
        rock: int = Query(0, ge=0, le=100000),
        mime: bool = False,
        gadsby: bool = False,
        authorization: str = Header(""),
        x_speaker: str = Header("", alias="X-Speaker"),
    ) -> dict:
        if token and not hmac.compare_digest(authorization, f"Bearer {token}"):
            raise HTTPException(401, "bad token")
        body = await request.body()
        if len(body) > MAX_SECONDS * SAMPLE_RATE * 2:
            raise HTTPException(413, f"max {MAX_SECONDS} s of audio")
        audio = np.frombuffer(body[: len(body) // 2 * 2], dtype="<i2").astype(np.float32) / 32768.0
        rules = Rules(frozenset(c.strip() for c in allow.split(",") if c.strip()), rock, mime, gadsby)
        if not rules.active or len(audio) < SAMPLE_RATE // 4:
            return {"violation": False, "severity": 0.0, "rule": None, "language": None, "p_allowed": 1.0, "ms": 0}

        t0 = time.perf_counter()
        engine = state["engine"]

        def run():
            a = engine.analyze(audio)
            return judge(rules, a.seconds, a.probs, a.decode, th)

        verdict = await run_in_threadpool(run)
        ms = round((time.perf_counter() - t0) * 1000)
        log.info("%s %.1fs allow=%s rock=%d -> %s %s sev=%.2f p_ok=%.2f %dms%s", x_speaker or "?", len(audio) / SAMPLE_RATE,
                 allow or "-", rock, "VIOLATION" if verdict.violation else "ok", verdict.rule or verdict.language,
                 verdict.severity, verdict.p_allowed, ms, f" {verdict.transcript!r}" if log_transcripts and verdict.transcript else "")
        return {**asdict(verdict), "ms": ms}

    return app


app = create_app()
