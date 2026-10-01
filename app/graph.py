"""Agent core. LangGraph StateGraph when installed, otherwise an equivalent sequential loop."""
from __future__ import annotations

import re
from typing import Any, Callable, TypedDict

from . import llm, tools
from .agents import action_agent, document_agent, scheme_agent

DISCLAIMER = ("NyayaMitra gives general guidance, not legal advice. Scheme limits and rules change: confirm on the "
              "official portal. Document checks verify format and checksum only, not live registry status.")


class State(TypedDict, total=False):
    text: str
    file_bytes: bytes
    filename: str
    lang: dict
    profile: dict
    needs: list
    assumptions: list
    plan_steps: list
    docs_result: dict
    matches: list
    actions: dict
    result: dict


def build_nodes(emit: Callable[[dict], None]):
    def step(stage, agent, title, detail=None):
        emit({"type": "step", "stage": stage, "agent": agent, "title": title, "detail": detail})

    def tool_cb(stage, agent):
        return lambda name, args, out: emit({"type": "tool", "stage": stage, "agent": agent, "tool": name,
                                             "input": args, "output": out})

    def n_understand(s: State) -> dict:
        text = s.get("text", "")
        step("understand", "Core", "Reading the request", f"{len(text)} characters"
             + (f" + file {s['filename']}" if s.get("file_bytes") else ""))
        lang = tools.detect_language(text)
        tool_cb("understand", "Core")("detect_language", {}, lang)
        profile = tools.extract_profile(text)
        llm_p = llm.complete_json(
            "Extract an Indian small-business / citizen profile. Keys: segments (subset of street_vendor, food, "
            "food_processing, manufacturing, trader, service, artisan, grievance_payment, grievance_eviction, "
            "grievance_consumer, grievance_govt), state (string|null), turnover (rupees number|null), "
            "employees (int|null), women (bool|null), sc_st (bool|null), wants_loan (bool).", text) if text else None
        if llm_p:
            for seg in llm_p.get("segments") or []:
                if seg not in profile["segments"]:
                    profile["segments"].append(seg)
            for k in ("state", "turnover", "employees", "women", "sc_st"):
                if profile.get(k) is None and llm_p.get(k) is not None:
                    profile[k] = llm_p[k]
            profile["wants_loan"] = profile["wants_loan"] or bool(llm_p.get("wants_loan"))
        if any(x in profile["segments"] for x in tools.BUSINESS_SEGMENTS) and "business" not in profile["segments"]:
            profile["segments"].append("business")
        tool_cb("understand", "Core")("extract_profile", {"llm_assist": bool(llm_p)}, {
            k: v for k, v in profile.items() if k != "has"} | {"has": {k: v for k, v in profile["has"].items() if v is not None}})
        return {"lang": lang, "profile": profile}

    def n_reason(s: State) -> dict:
        p, needs, assume = s["profile"], [], []
        segs = set(p["segments"])
        biz = "business" in segs
        if biz and not p["has"].get("udyam"):
            needs.append("Formal MSME identity (Udyam)")
        if "street_vendor" in segs and not p["has"].get("vending_cert"):
            needs.append("Street-vendor recognition (Certificate of Vending / ULB letter)")
        if "food" in segs and not p["has"].get("fssai"):
            needs.append("Food-safety authorisation (FSSAI)")
        if biz and not p["has"].get("trade_license") and "street_vendor" not in segs:
            needs.append("Local trade licence")
        if p["wants_loan"]:
            needs.append("Credit options without collateral")
        for g, label in (("grievance_payment", "Recover delayed payment"), ("grievance_eviction", "Stop eviction / harassment"),
                         ("grievance_consumer", "Consumer complaint"), ("grievance_govt", "Public grievance filing")):
            if g in segs:
                needs.append(label)
        if biz and p["turnover"] is None:
            assume.append("Turnover not stated: treating as a micro enterprise; GST and FSSAI thresholds need confirmation")
        if biz and not p.get("state"):
            assume.append("State not stated: using central schemes; state/municipal steps are generic")
        if not segs:
            assume.append("Could not identify a business or grievance type: describe what you do or what went wrong")
        step("reason", "Core", "Identified needs", "; ".join(needs) or "none identified")
        if assume:
            step("reason", "Core", "Assumptions", "; ".join(assume))
        return {"needs": needs, "assumptions": assume}

    def n_plan(s: State) -> dict:
        has_docs = bool(s.get("file_bytes")) or bool(tools.validate_documents(s.get("text", "")))
        steps = []
        if has_docs:
            steps.append({"agent": "Document & OCR Agent", "goal": "Parse uploaded or pasted documents and validate identifiers"})
        steps.append({"agent": "Scheme & Compliance Agent", "goal": "Match knowledge-base schemes and check eligibility"})
        steps.append({"agent": "Action & Workflow Agent", "goal": "Build roadmap, pre-filled forms and draft letters"})
        step("plan", "Core", "Execution plan", " -> ".join(x["agent"] for x in steps))
        return {"plan_steps": steps}

    def n_tools(s: State) -> dict:
        p = s["profile"]
        docs_result = {"findings": [], "fields": {}, "ocr_method": None, "ocr_note": ""}
        if any(x["agent"].startswith("Document") for x in s["plan_steps"]):
            step("tools", "Document & OCR Agent", "Running", None)
            docs_result = document_agent.run(s.get("text", ""), s.get("file_bytes"), s.get("filename", ""),
                                             tool_cb("tools", "Document & OCR Agent"))
            # feedback loop: verified documents update the profile used for matching
            for f in docs_result["findings"]:
                if f["status"] != "invalid":
                    key = {"Udyam Registration": "udyam", "GSTIN": "gst", "FSSAI licence/registration": "fssai"}.get(f["type"])
                    if key:
                        p["has"][key] = True
                    if f["type"] == "GSTIN" and f.get("extracted", {}).get("state") and not p.get("state"):
                        p["state"] = f["extracted"]["state"]
            step("tools", "Core", "Profile updated from documents",
                 ", ".join(k for k, v in p["has"].items() if v) or "no valid registrations found")
        step("tools", "Scheme & Compliance Agent", "Running", None)
        matches = scheme_agent.run(p, s.get("text", ""), tool_cb("tools", "Scheme & Compliance Agent"))
        return {"docs_result": docs_result, "matches": matches, "profile": p}

    def n_act(s: State) -> dict:
        step("act", "Action & Workflow Agent", "Running", None)
        actions = action_agent.run(s["profile"], s["matches"], s["docs_result"], s.get("text", ""), s["lang"],
                                   tool_cb("act", "Action & Workflow Agent"))
        return {"actions": actions}

    def n_deliver(s: State) -> dict:
        p, m, a = s["profile"], s["matches"], s["actions"]
        shown = [x for x in m if x["status"] in ("likely_eligible", "check_eligibility")]
        docs = s["docs_result"]["findings"]
        bad = [d for d in docs if d["status"] in ("invalid", "expired")]
        parts = [f"Language: {s['lang']['name']}."]
        if shown:
            parts.append(f"{len(shown)} schemes / compliance items match. Start with: "
                         + ", ".join(r["name"] for r in a["roadmap"][:3]) + ".")
        else:
            parts.append("No schemes matched yet. Add what you sell, where, and what went wrong.")
        if docs:
            parts.append(f"{len(docs)} document identifier(s) checked; {len(bad)} need attention." if bad
                         else f"{len(docs)} document identifier(s) checked; all passed format checks.")
        if a["letters"]:
            parts.append(f"{len(a['letters'])} draft letter(s) ready.")
        summary = " ".join(parts)
        result = {"language": s["lang"], "summary": summary, "profile": {k: v for k, v in p.items()},
                  "assumptions": s["assumptions"], "needs": s["needs"], "documents": docs,
                  "doc_fields": s["docs_result"]["fields"],
                  "schemes": [x for x in m if x["status"] != "not_applicable"],
                  "ruled_out": len([x for x in m if x["status"] == "not_applicable"]),
                  **a, "llm_assisted": llm.available(), "disclaimer": DISCLAIMER}
        step("deliver", "Core", "Packaging result", summary)
        emit({"type": "final", "result": result})
        return {"result": result}

    return [("n_understand", n_understand), ("n_reason", n_reason), ("n_plan", n_plan),
            ("n_tools", n_tools), ("n_act", n_act), ("n_deliver", n_deliver)]


def run_pipeline(text: str, file_bytes: bytes | None, filename: str, emit: Callable[[dict], None]) -> dict:
    text = (text or "").strip()
    if not text and not file_bytes:
        emit({"type": "error", "message": "Describe your business or problem, or upload a document."})
        return {}
    nodes = build_nodes(emit)
    init: State = {"text": text, "filename": filename or ""}
    if file_bytes:
        init["file_bytes"] = file_bytes
    try:
        from langgraph.graph import END, StateGraph

        g = StateGraph(State)
        for name, fn in nodes:
            g.add_node(name, fn)
        g.set_entry_point(nodes[0][0])
        for (a, _), (b, _) in zip(nodes, nodes[1:]):
            g.add_edge(a, b)
        g.add_edge(nodes[-1][0], END)
        return g.compile().invoke(init)
    except ImportError:
        state: dict[str, Any] = dict(init)
        for _, fn in nodes:
            state.update(fn(state))  # type: ignore[arg-type]
        return state
