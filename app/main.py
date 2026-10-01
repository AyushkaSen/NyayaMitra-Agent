"""FastAPI entrypoint: streams agent events over Server-Sent Events and serves the UI."""
from __future__ import annotations

import json
import os
import queue
import threading
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import llm
from .graph import run_pipeline
from .vector_index import load_kb

MAX_BYTES = 5 * 1024 * 1024
PACE = float(os.getenv("NYAYA_PACE", "0.2"))  # seconds between streamed events, for a readable live trace

app = FastAPI(title="NyayaMitra-Agent", version="0.1.0")


@app.get("/api/health")
def health():
    return {"status": "ok", "llm": llm.available(), "schemes": len(load_kb())}


@app.get("/api/schemes")
def schemes():
    return [{k: s[k] for k in ("id", "name", "kind", "level", "desc", "url")} for s in load_kb()]


async def _read(file: Optional[UploadFile]):
    if file is None or not file.filename:
        return None, ""
    data = await file.read()
    return (data[:MAX_BYTES] if data else None), file.filename


@app.post("/api/run")
async def run_stream(text: str = Form(""), file: Optional[UploadFile] = File(None)):
    data, name = await _read(file)
    q: queue.Queue = queue.Queue()
    n = {"i": 0}

    def emit(ev: dict):
        n["i"] += 1
        q.put({**ev, "seq": n["i"], "ts": round(time.time(), 2)})
        if ev.get("type") != "final":
            time.sleep(PACE)

    def worker():
        try:
            run_pipeline(text, data, name, emit)
        except Exception as e:  # noqa: BLE001
            q.put({"type": "error", "message": f"Agent failed: {e}"})
        finally:
            q.put(None)

    threading.Thread(target=worker, daemon=True).start()

    def gen():
        while (ev := q.get()) is not None:
            yield f"data: {json.dumps(ev, ensure_ascii=False, default=str)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/run_sync")
async def run_sync(text: str = Form(""), file: Optional[UploadFile] = File(None)):
    """Non-streaming variant: returns the final result plus the full trace (used by agent.yaml)."""
    data, name = await _read(file)
    events: list[dict] = []
    run_pipeline(text, data, name, events.append)
    final = next((e["result"] for e in events if e["type"] == "final"), None)
    err = next((e["message"] for e in events if e["type"] == "error"), None)
    if err:
        return JSONResponse({"error": err}, status_code=400)
    return {"result": final, "trace": [e for e in events if e["type"] != "final"]}


app.mount("/", StaticFiles(directory=Path(__file__).resolve().parent.parent / "static", html=True), name="ui")
