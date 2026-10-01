"""Action & Workflow Agent: roadmap, auto-filled forms and formal draft letters."""
from __future__ import annotations

import datetime as dt

from .. import llm, tools

FILL = "<<fill>>"
PHASE = {1: "Do first", 2: "Next", 3: "When you are ready"}


def _rs(v):
    return f"₹{v:,.0f}" if v else "₹[amount]"


def _first(docs, kind):
    return next((d for d in docs if d["type"] == kind and d["status"] != "invalid"), None)


def build_forms(p, recs, docs, fields):
    ids = {m["id"] for m in recs}
    forms = []
    pan = _first(docs, "PAN")
    segs = set(p["segments"])
    activity = "Manufacturing" if "manufacturing" in segs else "Services"
    nic = ("56 - Food and beverage service activities" if "food" in segs
           else "47 - Retail trade" if "trader" in segs or "street_vendor" in segs else FILL)
    if "udyam" in ids:
        forms.append({"id": "udyam", "title": "Udyam Registration: pre-filled sheet",
                      "portal": "https://udyamregistration.gov.in",
                      "fields": {
                          "Name of entrepreneur": fields.get("owner_name", FILL),
                          "Type of organisation": FILL,
                          "Aadhaar number": "Enter on the portal only. Not collected here",
                          "PAN": pan["value"] if pan else FILL,
                          "Enterprise name": fields.get("business_name", FILL),
                          "State": p.get("state") or FILL,
                          "PIN code": fields.get("pincode", FILL),
                          "Major activity": activity,
                          "NIC activity (suggested)": nic,
                          "Employees": p["employees"] if p.get("employees") is not None else FILL,
                          "Annual turnover (₹)": int(p["turnover"]) if p.get("turnover") else FILL,
                          "Investment in plant & machinery (₹)": FILL,
                          "Bank account / IFSC": FILL}})
    if "pm_svanidhi" in ids:
        forms.append({"id": "svanidhi", "title": "PM SVANidhi: pre-filled sheet",
                      "portal": "https://pmsvanidhi.mohua.gov.in",
                      "fields": {"Applicant name": fields.get("owner_name", FILL),
                                 "Aadhaar (eKYC on portal)": "Enter on the portal only",
                                 "Mobile linked to Aadhaar": FILL,
                                 "Type of vending": ", ".join(s.replace("_", " ") for s in segs
                                                              if s in ("food", "trader", "service", "street_vendor")) or FILL,
                                 "Vending location / ward": FILL,
                                 "Urban Local Body": FILL,
                                 "Vending certificate / LoR number": "Request LoR from ULB" if not p["has"].get("vending_cert") else FILL,
                                 "Bank and IFSC": FILL,
                                 "Tranche requested": "First"}})
    return forms


def build_letters(p, text, docs):
    today = dt.date.today()
    d = today.strftime("%d %B %Y")
    segs = set(p["segments"])
    ud = _first(docs, "Udyam Registration")
    letters = []

    if "grievance_payment" in segs:
        dates = tools.find_dates(text)
        inv = next((x["date"] for x in dates if any(w in x["ctx"] for w in ("invoice", "bill", "dated", "inv"))),
                   dates[0]["date"] if dates else None)
        due = (inv + dt.timedelta(days=45)).strftime("%d %B %Y") if inv else "[invoice date + 45 days]"
        letters.append({"title": "Demand notice for delayed payment (MSMED Act, 2006)", "to": "Buyer", "body": f"""Date: {d}

To,
[Buyer's name and designation]
[Buyer's address]

Subject: Notice for payment of {_rs(p.get('dispute_amount'))} due for goods/services supplied (Sections 15 and 16, MSMED Act, 2006)

Sir/Madam,

We, [Your enterprise name] ({ud['value'] if ud else 'Udyam No. [fill]'}), are a registered micro/small enterprise. We supplied goods/services to you against invoice no. [fill] dated {inv.strftime('%d %B %Y') if inv else '[date]'}. The amount of {_rs(p.get('dispute_amount'))} remains unpaid.

Under Section 15 of the MSMED Act, 2006, payment is due on the agreed date, which cannot exceed 45 days from the day of acceptance of the goods or services. The due date for this invoice was {due}.

Under Section 16, you are liable to pay compound interest with monthly rests at three times the bank rate notified by the Reserve Bank of India, from the due date until payment.

Please pay the principal and interest within 15 days of receiving this notice. Otherwise we will file a reference with the Micro and Small Enterprises Facilitation Council under Section 18 through the MSME Samadhaan portal and pursue all other remedies available to us.

Yours faithfully,
[Name, designation, mobile, address]
Enclosures: invoice(s), delivery proof, Udyam certificate, earlier reminders"""})

    if "grievance_eviction" in segs or ("street_vendor" in segs and not p["has"].get("vending_cert")):
        evict = "grievance_eviction" in segs
        letters.append({"title": "Application to Town Vending Committee" + (" against eviction without due process" if evict else ""),
                        "to": "Member Secretary, Town Vending Committee / Municipal Commissioner", "body": f"""Date: {d}

To,
The Member Secretary, Town Vending Committee
[Municipality / Municipal Corporation name]

Subject: Request for enrolment and Certificate of Vending under the Street Vendors (Protection of Livelihood and Regulation of Street Vending) Act, 2014

Sir/Madam,

I, [Your name], have been vending [goods/services] at [location, ward no.] since [year]. {'My cart/goods have been removed or penalised without a survey, notice or relocation. ' if evict else ''}

I request that you (1) enrol me in the street-vendor survey, (2) issue my Certificate of Vending / ID card, and (3) issue a Letter of Recommendation so that I can apply for PM SVANidhi. {'I also request that no further eviction or seizure take place until the survey and the due-process requirements of the Act are completed, and that this letter be treated as a grievance before the Town Vending Committee.' if evict else ''}

Enclosed are my identity and address proof and evidence of vending (photographs, witness statement).

Yours faithfully,
[Name, mobile number, address]"""})

    if "grievance_consumer" in segs:
        letters.append({"title": "Consumer notice to seller / service provider", "to": "Seller", "body": f"""Date: {d}

To,
[Seller / service provider name and address]

Subject: Notice for refund / replacement / compensation

Sir/Madam,

On [date] I purchased [product/service] for ₹[amount] (invoice no. [fill]). It is [defective / not delivered / not as described]: [short description].

Please refund / replace / compensate me within 15 days of this notice. Otherwise I will approach the National Consumer Helpline (1915) and file a complaint before the appropriate Consumer Commission through e-Daakhil.

Yours faithfully,
[Name, mobile, address]
Enclosures: invoice, photos, earlier messages"""})

    if "grievance_govt" in segs:
        letters.append({"title": "CPGRAMS grievance text", "to": "Concerned Ministry / Department", "body": f"""Subject: Delay in [service / certificate / benefit] applied on [date]

I applied for [service] on [date] with application number [fill] at [office / portal]. Despite the prescribed time having passed, no decision or reason has been communicated.

I request that the application be processed or the reasons for rejection be recorded in writing, with a timeline for resolution.

Name: [fill]    Mobile: [fill]    Address: [fill]"""})
    return letters


def run(profile, matches, docs_result, text, lang, tool):
    recs = [m for m in matches if m["status"] in ("likely_eligible", "check_eligibility")]
    recs.sort(key=lambda m: (m["priority"], -m["score"]))
    done = [m for m in matches if m["status"] == "already_have"]
    roadmap = [{"scheme_id": m["id"], "name": m["name"], "phase": PHASE[m["priority"]], "status": m["status"],
                "steps": m["steps"], "docs": m["docs"], "url": m["url"], "missing": m["missing"]} for m in recs[:7]]
    tool("build_roadmap", {"recommended": len(recs)}, [f"{r['phase']}: {r['name']}" for r in roadmap])

    docs_needed = list(dict.fromkeys(d for r in roadmap for d in r["docs"]))
    forms = build_forms(profile, recs[:7], docs_result["findings"], docs_result["fields"])
    tool("prefill_forms", {}, [f["title"] for f in forms] or "none needed")
    letters = build_letters(profile, text, docs_result["findings"])
    tool("draft_letters", {}, [l["title"] for l in letters] or "none needed")

    if lang["code"] not in ("en", "hi-Latn") and letters:
        for l in letters:
            loc = llm.localize(l["body"], lang["name"])
            if loc:
                l["body_local"], l["local_language"] = loc, lang["name"]
        tool("localize_letters", {"language": lang["name"]},
             "translated" if any("body_local" in l for l in letters)
             else "skipped (set ANTHROPIC_API_KEY to enable translation)")
    return {"roadmap": roadmap, "already_done": [m["name"] for m in done],
            "documents_needed": docs_needed, "forms": forms, "letters": letters}
