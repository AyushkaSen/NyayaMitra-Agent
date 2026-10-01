"""Scheme & Compliance Matching Agent: semantic retrieval + explicit eligibility rules."""
from __future__ import annotations

from ..vector_index import get_index, load_kb

WEIGHT = {"likely_eligible": 1.0, "check_eligibility": 0.55, "already_have": 0.2, "not_applicable": 0.0}


def _lakh(v: float) -> str:
    return f"₹{v / 1e5:g} lakh"


def evaluate(s: dict, p: dict) -> tuple[str, list[str], list[str]]:
    r, reasons, missing = s.get("rules", {}), [], []
    status = "likely_eligible"
    segs = set(p["segments"])

    want = set(r.get("segments_any", []))
    if want:
        hit = sorted(segs & want)
        if hit:
            reasons.append("Fits your profile: " + ", ".join(h.replace("_", " ") for h in hit))
        else:
            return "not_applicable", ["Aimed at: " + ", ".join(w.replace("_", " ") for w in sorted(want))], []

    if r.get("group_any"):
        have = [g for g in r["group_any"] if p.get(g)]
        if have:
            reasons.append("Applicant group matches: " + ", ".join(have).replace("_", "/"))
        else:
            status = "check_eligibility"
            missing.append("Whether the applicant is a woman or from SC/ST (required for this scheme)")

    if r.get("turnover_min"):
        t = p.get("turnover")
        if t is None:
            status = "check_eligibility"
            missing.append("Annual turnover (to see if GST is mandatory)")
        elif t >= r["turnover_min"]:
            reasons.append(f"Turnover about {_lakh(t)} is above the GST thresholds")
        else:
            status = "check_eligibility"
            reasons.append(f"Turnover about {_lakh(t)} is below the usual threshold; optional unless you sell "
                           "across states or online")

    if s["id"] == "fssai" and p.get("turnover") is not None:
        reasons.append("Basic registration is likely enough" if p["turnover"] <= 1.2e6
                       else "Turnover is above ₹12 lakh, so a State/Central licence is likely required")
    if s["id"] == "pm_svanidhi" and not p["has"].get("vending_cert"):
        missing.append("Certificate of Vending or ULB Letter of Recommendation")
    if s["id"] == "pmegp":
        reasons.append("Only for new units, not for expanding an existing subsidised unit")
        status = "check_eligibility" if status == "likely_eligible" else status
    if s["id"] == "cgtmse" and not p.get("wants_loan"):
        status = "check_eligibility"
        reasons.append("Relevant if a bank asks for collateral on a business loan")
    if s["id"] in ("mudra",) and p.get("wants_loan"):
        reasons.append("You mentioned needing credit")

    skip = r.get("skip_if_has")
    if skip and p["has"].get(skip):
        return "already_have", [f"You indicated you already hold this ({skip.replace('_', ' ')})"], []
    return status, reasons, missing


def run(profile: dict, text: str, tool) -> list[dict]:
    kb = load_kb()
    q = " ".join([text] + [s.replace("_", " ") for s in profile["segments"]] + (["loan credit"] if profile["wants_loan"] else []))
    hits = dict(get_index().search(q, k=len(kb)))
    top = max(hits.values()) or 1.0
    tool("kb_search", {"index": "tfidf over schemes.json", "k": len(kb), "query_tokens": len(q.split())},
         [f"{k}: {v:.2f}" for k, v in sorted(hits.items(), key=lambda x: -x[1])[:5]])

    out = []
    for s in kb:
        status, reasons, missing = evaluate(s, profile)
        sem = hits.get(s["id"], 0.0) / top
        boost = 0.1 if s.get("rules", {}).get("boost_if_loan") and profile["wants_loan"] else 0.0
        out.append({**{k: s[k] for k in ("id", "name", "kind", "level", "priority", "desc", "benefit", "eligibility",
                                         "docs", "steps", "url")},
                    "status": status, "reasons": reasons, "missing": missing,
                    "score": round(0.6 * WEIGHT[status] + 0.4 * sem + boost, 3)})
    out.sort(key=lambda m: -m["score"])
    tool("check_eligibility", {"profile_segments": profile["segments"], "turnover": profile["turnover"]},
         {m["id"]: m["status"] for m in out if m["status"] != "not_applicable"})
    return out
