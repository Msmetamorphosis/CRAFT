"""
main.py - CRAFT FastAPI backend
Contextual Rewriting and Fitness Tester

Endpoints:
  GET  /api/health     - health check
  GET  /api/task-types - return task type metadata
  POST /api/analyze    - full prompt analysis pipeline (SSE streaming)
"""

import json
import time
import asyncio
from pathlib import Path

import anthropic
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from config import MODEL_DEFAULT, TASK_LABELS, TASK_DESCRIPTIONS
from classifier import classify_prompt
from auditor import audit_prompt
from rewriter import rewrite_prompt
from evaluator import evaluate_output

app = FastAPI(title="CRAFT API - Contextual Rewriting and Fitness Tester")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(str(frontend_dir / "index.html"))


# ── Request model ─────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    api_key:   str
    prompt:    str
    context:   str = ""        # optional additional context/document
    task_type: str = "auto"    # auto-detect or user override
    model:     str = MODEL_DEFAULT


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "CRAFT", "version": "1.0.0"}


@app.get("/api/task-types")
async def task_types():
    return {
        "task_types": [
            {"id": k, "label": TASK_LABELS[k], "description": TASK_DESCRIPTIONS[k]}
            for k in TASK_LABELS
        ]
    }


# ── SSE Analysis Pipeline ─────────────────────────────────────────────────────

async def analysis_stream(req: AnalyzeRequest):
    if not req.api_key.startswith("sk-ant-"):
        yield {"event": "error", "data": json.dumps({"message": "Invalid API key format."})}
        return

    try:
        client = anthropic.Anthropic(api_key=req.api_key)
    except Exception as e:
        yield {"event": "error", "data": json.dumps({"message": str(e)})}
        return

    full_prompt = req.prompt
    if req.context.strip():
        full_prompt = f"{req.prompt}\n\nContext/Document:\n{req.context}"

    model = req.model

    # Step 1: Classify
    yield {"event": "step", "data": json.dumps({
        "step": 1, "total_steps": 6,
        "label": "Classifying task type...",
        "status": "running"
    })}

    try:
        classification = await asyncio.get_event_loop().run_in_executor(
            None, classify_prompt, client, full_prompt, model
        )
        task_type = req.task_type if req.task_type != "auto" else classification["task_type"]

        yield {"event": "classification", "data": json.dumps({
            "step": 1, "status": "done",
            "task_type": task_type,
            "task_label": TASK_LABELS.get(task_type, task_type),
            "confidence": classification.get("confidence", 0),
            "reasoning": classification.get("reasoning", ""),
            "secondary_type": classification.get("secondary_type"),
            "secondary_confidence": classification.get("secondary_confidence")
        })}
    except Exception as e:
        yield {"event": "error", "data": json.dumps({"message": f"Classification failed: {e}"})}
        return

    await asyncio.sleep(0.1)

    # Step 2: Audit original prompt
    yield {"event": "step", "data": json.dumps({
        "step": 2, "total_steps": 6,
        "label": "Scoring original prompt...",
        "status": "running"
    })}

    try:
        original_audit = await asyncio.get_event_loop().run_in_executor(
            None, audit_prompt, client, full_prompt, task_type, model
        )
        yield {"event": "original_audit", "data": json.dumps({
            "step": 2, "status": "done",
            **original_audit
        })}
    except Exception as e:
        yield {"event": "error", "data": json.dumps({"message": f"Audit failed: {e}"})}
        return

    await asyncio.sleep(0.1)

    # Step 3: Run original prompt through LLM
    yield {"event": "step", "data": json.dumps({
        "step": 3, "total_steps": 6,
        "label": "Running original prompt through Claude...",
        "status": "running"
    })}

    try:
        start = time.perf_counter()
        def _call_original():
            msg = client.messages.create(
                model=model, max_tokens=1500,
                messages=[{"role": "user", "content": full_prompt}]
            )
            return msg.content[0].text

        original_output = await asyncio.get_event_loop().run_in_executor(None, _call_original)
        original_latency = round((time.perf_counter() - start) * 1000)

        yield {"event": "original_output", "data": json.dumps({
            "step": 3, "status": "done",
            "output": original_output,
            "latency_ms": original_latency
        })}
    except Exception as e:
        yield {"event": "error", "data": json.dumps({"message": f"LLM call failed: {e}"})}
        return

    await asyncio.sleep(0.1)

    # Step 4: Score original output
    yield {"event": "step", "data": json.dumps({
        "step": 4, "total_steps": 6,
        "label": "Evaluating original output quality...",
        "status": "running"
    })}

    try:
        original_eval = await asyncio.get_event_loop().run_in_executor(
            None, evaluate_output, client, full_prompt, original_output, task_type, model
        )
        yield {"event": "original_eval", "data": json.dumps({
            "step": 4, "status": "done",
            **original_eval
        })}
    except Exception as e:
        yield {"event": "error", "data": json.dumps({"message": f"Evaluation failed: {e}"})}
        return

    await asyncio.sleep(0.1)

    # Step 5: Rewrite prompt
    yield {"event": "step", "data": json.dumps({
        "step": 5, "total_steps": 6,
        "label": "Rewriting and improving prompt...",
        "status": "running"
    })}

    try:
        rewrite_result = await asyncio.get_event_loop().run_in_executor(
            None, rewrite_prompt, client, full_prompt, task_type, original_audit, model
        )
        improved_prompt = rewrite_result.get("rewritten_prompt", full_prompt)

        # Audit the rewritten prompt
        improved_audit = await asyncio.get_event_loop().run_in_executor(
            None, audit_prompt, client, improved_prompt, task_type, model
        )

        yield {"event": "rewrite", "data": json.dumps({
            "step": 5, "status": "done",
            "rewritten_prompt": improved_prompt,
            "changes_made": rewrite_result.get("changes_made", []),
            "placeholders_added": rewrite_result.get("placeholders_added", []),
            "user_action_required": rewrite_result.get("user_action_required"),
            "improved_audit": improved_audit
        })}
    except Exception as e:
        yield {"event": "error", "data": json.dumps({"message": f"Rewrite failed: {e}"})}
        return

    await asyncio.sleep(0.1)

    # Step 6: Run improved prompt through LLM and score
    yield {"event": "step", "data": json.dumps({
        "step": 6, "total_steps": 6,
        "label": "Running improved prompt through Claude...",
        "status": "running"
    })}

    try:
        start = time.perf_counter()
        def _call_improved():
            msg = client.messages.create(
                model=model, max_tokens=1500,
                messages=[{"role": "user", "content": improved_prompt}]
            )
            return msg.content[0].text

        improved_output = await asyncio.get_event_loop().run_in_executor(None, _call_improved)
        improved_latency = round((time.perf_counter() - start) * 1000)

        improved_eval = await asyncio.get_event_loop().run_in_executor(
            None, evaluate_output, client, improved_prompt, improved_output, task_type, model
        )

        output_lift = round(improved_eval.get("total_score", 0) - original_eval.get("total_score", 0))
        prompt_lift = round(improved_audit.get("total_score", 0) - original_audit.get("total_score", 0))

        yield {"event": "improved_output", "data": json.dumps({
            "step": 6, "status": "done",
            "output": improved_output,
            "latency_ms": improved_latency,
            "improved_eval": improved_eval
        })}

        yield {"event": "complete", "data": json.dumps({
            "prompt_score_before": original_audit.get("total_score", 0),
            "prompt_score_after":  improved_audit.get("total_score", 0),
            "prompt_lift":         prompt_lift,
            "output_score_before": original_eval.get("total_score", 0),
            "output_score_after":  improved_eval.get("total_score", 0),
            "output_lift":         output_lift,
            "ceiling_score":       original_audit.get("ceiling_score", 0),
            "task_type":           task_type,
            "llm_calls":           6
        })}

    except Exception as e:
        yield {"event": "error", "data": json.dumps({"message": f"Final evaluation failed: {e}"})}


@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    return EventSourceResponse(analysis_stream(req))
