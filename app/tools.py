"""Deterministic, offline tools shared by the agents (no network, no LLM)."""
from __future__ import annotations

import datetime as dt
import io
import re

# ----------------------------------------------------------------- language
SCRIPTS = [
    ("hi", "Hindi / Marathi (Devanagari)", 0x0900, 0x097F),
    ("bn", "Bengali", 0x0980, 0x09FF),
    ("pa", "Punjabi", 0x0A00, 0x0A7F),
    ("gu", "Gujarati", 0x0A80, 0x0AFF),
    ("or", "Odia", 0x0B00, 0x0B7F),
    ("ta", "Tamil", 0x0B80, 0x0BFF),
    ("te", "Telugu", 0x0C00, 0x0C7F),
    ("kn", "Kannada", 0x0C80, 0x0CFF),
    ("ml", "Malayalam", 0x0D00, 0x0D7F),
]


def detect_language(text: str) -> dict:
    counts: dict[str, int] = {}
    for ch in text:
        o = ord(ch)
        for code, _, lo, hi in SCRIPTS:
            if lo <= o <= hi:
                counts[code] = counts.get(code, 0) + 1
    if counts:
        code = max(counts, key=counts.get)
        name = next(n for c, n, _, _ in SCRIPTS if c == code)
        return {"code": code, "name": name}
    if re.search(r"\b(mera|meri|hai|nahi|dukan|chahiye|karna|kaise|paisa|loan chahiye)\b", text.lower()):
        return {"code": "hi-Latn", "name": "Hinglish (romanised Hindi)"}
    return {"code": "en", "name": "English"}


# ----------------------------------------------------------------- places
STATE_NAMES = {
    "west bengal": "West Bengal", "पश्चिम बंगाल": "West Bengal", "পশ্চিমবঙ্গ": "West Bengal",
    "kolkata": "West Bengal", "कोलकाता": "West Bengal", "কলকাতা": "West Bengal", "howrah": "West Bengal",
    "maharashtra": "Maharashtra", "mumbai": "Maharashtra", "pune": "Maharashtra", "मुंबई": "Maharashtra",
    "delhi": "Delhi", "दिल्ली": "Delhi", "uttar pradesh": "Uttar Pradesh", "lucknow": "Uttar Pradesh",
    "bihar": "Bihar", "patna": "Bihar", "karnataka": "Karnataka", "bengaluru": "Karnataka", "bangalore": "Karnataka",
    "tamil nadu": "Tamil Nadu", "chennai": "Tamil Nadu", "telangana": "Telangana", "hyderabad": "Telangana",
    "gujarat": "Gujarat", "ahmedabad": "Gujarat", "surat": "Gujarat", "rajasthan": "Rajasthan", "jaipur": "Rajasthan",
    "madhya pradesh": "Madhya Pradesh", "bhopal": "Madhya Pradesh", "odisha": "Odisha", "bhubaneswar": "Odisha",
    "assam": "Assam", "guwahati": "Assam", "kerala": "Kerala", "punjab": "Punjab", "haryana": "Haryana",
    "jharkhand": "Jharkhand", "ranchi": "Jharkhand",
}
GST_STATE_CODES = {"07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh", "10": "Bihar", "19": "West Bengal",
                   "24": "Gujarat", "27": "Maharashtra", "29": "Karnataka", "33": "Tamil Nadu", "36": "Telangana"}
UDYAM_STATE_CODES = set("AN AP AR AS BR CH CG DD DN DL GA GJ HR HP JK JH KA KL LA LD MP MH MN ML MZ NL OD PY PB RJ "
                        "SK TN TS TR UP UK WB".split())

# ----------------------------------------------------------------- lexicon
LEX = {
    "street_vendor": ["street vendor", "hawker", "handcart", "hand cart", "thela", "pushcart", "footpath", "pavement",
                      "stall", "फेरीवाला", "ठेला", "रेहड़ी", "पटरी", "ফেরিওয়ালা", "ঠেলা", "হকার", "ফুটপাথ"],
    "food": ["food", "tea", "chai", "restaurant", "dhaba", "bakery", "snack", "sweet", "tiffin", "canteen", "fssai",
             "juice", "biryani", "खाना", "चाय", "ढाबा", "मिठाई", "খাবার", "চা ", "মিষ্টি", "রেস্তোরাঁ"],
    "food_processing": ["pickle", "papad", "masala", "namkeen", "achar", "flour mill", "oil mill", "food processing",
                        "अचार", "पापड़", "আচার"],
    "manufacturing": ["manufactur", "factory", "production unit", "workshop", "fabricat", "small unit", "our unit",
                      "my unit", "कारखाना", "फैक्ट्री", "কারখানা", "উৎপাদন"],
    "trader": ["shop", "store", "kirana", "trading", "trader", "retail", "wholesale", "vegetable", "dukan",
               "दुकान", "सब्ज़ी", "सब्जी", "দোকান", "ব্যবসা", "সবজি"],
    "service": ["salon", "parlour", "parlor", "repair", "laundry", "courier", "cab ", "taxi", "cyber cafe",
                "photocopy", "सैलून", "পার্লার", "মেরামত"],
    "artisan": ["carpenter", "tailor", "potter", "weaver", "cobbler", "blacksmith", "goldsmith", "mason", "barber",
                "washerman", "sculptor", "artisan", "बढ़ई", "दर्जी", "कुम्हार", "जुलाहा", "মিস্ত্রি", "কামার",
                "কুমোর", "তাঁতি", "দর্জি"],
    "wants_loan": ["loan", "credit", "finance", "capital", "funding", "कर्ज", "लोन", "ऋण", "ঋণ", "লোন"],
    "grievance_payment": ["unpaid", "owes", "not paid", "hasn't paid", "delayed payment", "payment pending",
                          "overdue", "outstanding", "invoice", "भुगतान नहीं", "बकाया", "বকেয়া"],
    "grievance_eviction": ["evict", "removed my", "remove my", "cart removed", "bribe", "hafta", "extortion",
                           "seized", "confiscat", "penalty", "challan", "हटा", "बेदखल", "जब्त", "উচ্ছেদ", "তুলে দিচ্ছে"],
    "grievance_consumer": ["defective", "refund", "consumer", "cheated", "overcharg", "warranty", "ग्राहक",
                           "धोखा", "প্রতারণা", "ভোক্তা"],
    "grievance_govt": ["pension", "ration card", "application pending", "not processed", "corruption",
                       "सरकारी दफ्तर", "pending certificate"],
}
BUSINESS_SEGMENTS = ["street_vendor", "food", "food_processing", "manufacturing", "trader", "service", "artisan"]
WOMEN_RE = re.compile(r"\b(woman|women|female|ladies)\b|महिला|औरत|মহিলা|নারী", re.I)
SCST_RE = re.compile(r"scheduled (caste|tribe)|\bsc/st\b|अनुसूचित|তফসিলি", re.I)
DOC_WORDS = {
    "udyam": ["udyam", "उद्यम", "উদ্যম"],
    "gst": ["gst", "जीएसटी", "জিএসটি"],
    "fssai": ["fssai"],
    "trade_license": ["trade licen", "trade licence", "ट्रेड लाइसेंस", "ট্রেড লাইসেন্স"],
    "vending_cert": ["vending certificate", "vending id", "certificate of vending", "vendor id"],
}
NEG = ["no ", "not ", "don't", "dont", "without", "never", "नहीं", "नही", "বিনা", "নেই", "না "]
INTENT = ["apply", "want", "need", "how to", "get ", "register", "चाहिए", "कैसे", "চাই", "লাগবে", "দরকার", "बनवाना"]


def _status_of(low: str, kws: list[str]):
    for k in kws:
        i = low.find(k)
        if i < 0:
            continue
        ctx = low[max(0, i - 35): i + len(k) + 35]
        if any(n in ctx for n in NEG):
            return False
        if any(w in ctx for w in INTENT):
            return None
        return True
    return None


# ----------------------------------------------------------------- amounts
_UNITS = {"lakh": 1e5, "lakhs": 1e5, "lac": 1e5, "lacs": 1e5, "crore": 1e7, "crores": 1e7, "cr": 1e7, "k": 1e3,
          "thousand": 1e3, "hazar": 1e3, "हज़ार": 1e3, "हजार": 1e3, "लाख": 1e5, "करोड़": 1e7,
          "লাখ": 1e5, "হাজার": 1e3, "কোটি": 1e7}
_AMT = re.compile(r"(₹|rs\.?|inr)?\s*(\d[\d,]*(?:\.\d+)?)\s*"
                  r"(lakhs?|lacs?|crores?|cr\b|k\b|thousand|hazar|हज़ार|हजार|लाख|करोड़|লাখ|হাজার|কোটি)?", re.I)
DATE_RE = re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b|\b(\d{4})-(\d{2})-(\d{2})\b")


def _clean_for_amounts(text: str) -> str:
    t = DATE_RE.sub(" ", text)
    return re.sub(r"[\w-]*\d[\w-]*", lambda m: m.group(0) if len(m.group(0)) < 9 else " ", t)


def amounts_near(text: str, kws: list[str], span: int = 45):
    low = _clean_for_amounts(text).lower()
    for k in kws:
        for km in re.finditer(re.escape(k), low):
            win = low[max(0, km.start() - span): km.end() + span]
            for m in _AMT.finditer(win):
                val = float(m.group(2).replace(",", "")) * _UNITS.get((m.group(3) or "").lower(), 1.0)
                if m.group(1) or m.group(3) or val >= 1000:
                    return val
    return None


def find_dates(text: str) -> list[dict]:
    out = []
    for m in DATE_RE.finditer(text):
        try:
            d = (dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m.group(1)
                 else dt.date(int(m.group(4)), int(m.group(5)), int(m.group(6))))
        except ValueError:
            continue
        out.append({"date": d, "ctx": text[max(0, m.start() - 30): m.start()].lower()})
    return out


# ----------------------------------------------------------------- profile
def extract_profile(text: str) -> dict:
    low = text.lower()
    segs = [s for s, kws in LEX.items() if any(k in low for k in kws)]
    if "food_processing" in segs and "food" not in segs:
        segs.append("food")
    if any(s in segs for s in BUSINESS_SEGMENTS):
        segs.append("business")
    emp = re.search(r"(\d+)\s*(?:employees?|workers?|staff|helpers?|people|कर्मचारी|कर्मचारियों|লোক|কর্মী|কর্মচারী)", text, re.I)
    state = next((v for k, v in STATE_NAMES.items() if k in low), None)
    return {
        "segments": [s for s in segs if not s.startswith("wants_")],
        "wants_loan": "wants_loan" in segs,
        "state": state,
        "turnover": amounts_near(text, ["turnover", "sales", "revenue", "income", "कारोबार", "बिक्री", "বিক্রি", "আয়"]),
        "dispute_amount": amounts_near(text, ["owes", "due", "unpaid", "outstanding", "pending", "बकाया", "বকেয়া"]),
        "employees": int(emp.group(1)) if emp else None,
        "women": True if WOMEN_RE.search(text) else None,
        "sc_st": True if SCST_RE.search(text) else None,
        "has": {k: _status_of(low, v) for k, v in DOC_WORDS.items()},
    }


# ----------------------------------------------------------------- validators
_CS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_D = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 0, 6, 7, 8, 9, 5], [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
      [3, 4, 0, 1, 2, 8, 9, 5, 6, 7], [4, 0, 1, 2, 3, 9, 5, 6, 7, 8], [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
      [6, 5, 9, 8, 7, 1, 0, 4, 3, 2], [7, 6, 5, 9, 8, 2, 1, 0, 4, 3], [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
      [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]]
_P = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 5, 7, 6, 2, 8, 3, 0, 9, 4], [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
      [8, 9, 1, 6, 0, 4, 3, 5, 2, 7], [9, 4, 5, 3, 1, 2, 6, 8, 7, 0], [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
      [2, 7, 9, 3, 8, 0, 6, 4, 1, 5], [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]]
PAN_TYPES = {"P": "Individual", "C": "Company", "H": "HUF", "F": "Firm / LLP", "A": "Association of persons",
             "T": "Trust", "B": "Body of individuals", "L": "Local authority", "J": "Artificial juridical person",
             "G": "Government"}


def verhoeff_ok(num: str) -> bool:
    c = 0
    for i, ch in enumerate(reversed(num)):
        c = _D[c][_P[i % 8][int(ch)]]
    return c == 0


def gstin_checksum_ok(g: str) -> bool:
    tot = 0
    for i, ch in enumerate(g[:14]):
        v = _CS.index(ch) * (1 if i % 2 == 0 else 2)
        tot += v // 36 + v % 36
    return _CS[(36 - tot % 36) % 36] == g[14]


def _doc(kind, shown, checks, expiry=None, today=None):
    ok = all(c["ok"] for c in checks)
    status = "valid_format" if ok else "invalid"
    if ok and expiry and today and expiry < today:
        status = "expired"
    return {"type": kind, "value": shown, "status": status, "checks": checks,
            "expiry": expiry.isoformat() if expiry else None,
            "note": "Format and checksum only. Confirm the live status on the official portal."}


def validate_documents(text: str, today: dt.date | None = None) -> list[dict]:
    today = today or dt.date.today()
    up = text.upper()
    docs: list[dict] = []
    exp_dates = [d["date"] for d in find_dates(text)
                 if any(w in d["ctx"] for w in ("valid", "expiry", "expires", "upto", "up to", "till"))]
    expiry = exp_dates[0] if exp_dates else None

    for m in dict.fromkeys(re.findall(r"UDYAM[-\s]?[A-Z]{2}[-\s]?\d{2}[-\s]?\d{7}", up)):
        v = re.sub(r"[-\s]", "", m)
        st, yr, n = v[5:7], v[7:9], v[9:]
        shown = f"UDYAM-{st}-{yr}-{n}"
        docs.append(_doc("Udyam Registration", shown, [
            {"name": "Pattern UDYAM-XX-00-0000000", "ok": True},
            {"name": f"State code '{st}' is a valid state/UT code", "ok": st in UDYAM_STATE_CODES}], expiry=None))

    for g in dict.fromkeys(re.findall(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9]{3}\b", up)):
        strict = bool(re.fullmatch(r"\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]", g))
        sc = g[:2]
        checks = [
            {"name": "15-character GSTIN structure (state + PAN + entity + Z + check)", "ok": strict},
            {"name": f"State code {sc} is valid", "ok": (1 <= int(sc) <= 38) or sc in ("97", "99")},
            {"name": "Check digit matches", "ok": strict and gstin_checksum_ok(g)},
        ]
        d = _doc("GSTIN", g, checks, expiry=None)
        d["extracted"] = {"state": GST_STATE_CODES.get(sc), "embedded_pan": g[2:12]}
        docs.append(d)

    for p in dict.fromkeys(re.findall(r"\b[A-Z]{5}\d{4}[A-Z]\b", up)):
        t = PAN_TYPES.get(p[3])
        d = _doc("PAN", p, [{"name": "Pattern AAAAA0000A", "ok": True},
                            {"name": "4th letter is a valid holder type", "ok": t is not None}])
        d["extracted"] = {"holder_type": t}
        docs.append(d)

    for a in dict.fromkeys(re.findall(r"\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b", up)):
        n = re.sub(r"\s", "", a)
        d = _doc("Aadhaar-format number", f"XXXX XXXX {n[-4:]}",
                 [{"name": "12 digits, first digit 2-9", "ok": True},
                  {"name": "Verhoeff check digit matches", "ok": verhoeff_ok(n)}])
        d["note"] = "Masked for privacy. Aadhaar is never stored; enter it only on the official portal."
        docs.append(d)

    if "FSSAI" in up or "FOOD SAFETY" in up:
        for f in dict.fromkeys(re.findall(r"\b\d{14}\b", up)):
            docs.append(_doc("FSSAI licence/registration", f, [
                {"name": "14 digits", "ok": True},
                {"name": "Starts with 1 or 2 (registration/licence)", "ok": f[0] in "12"}], expiry=expiry, today=today))
    return docs


def extract_fields(text: str) -> dict:
    f: dict = {}
    m = re.search(r"(?:enterprise name|name of (?:the )?(?:enterprise|firm|business)|legal name|trade name)\s*[:\-]\s*(.+)",
                  text, re.I)
    if m:
        f["business_name"] = m.group(1).strip()[:80]
    m = re.search(r"\b\d{6}\b", text)
    if m:
        f["pincode"] = m.group(0)
    m = re.search(r"(?:proprietor|owner|name)\s*[:\-]\s*([A-Za-z .]{3,40})", text, re.I)
    if m:
        f["owner_name"] = m.group(1).strip()
    return f


# ----------------------------------------------------------------- OCR
def extract_text(data: bytes, filename: str):
    """Returns (text, method, note)."""
    n = (filename or "").lower()
    try:
        if n.endswith(".pdf"):
            from pypdf import PdfReader
            t = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
            return t, "pypdf", ("" if t.strip() else "No text layer; upload scanned pages as images for OCR.")
        if n.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff")):
            import pytesseract
            from PIL import Image
            img = Image.open(io.BytesIO(data))
            try:
                t = pytesseract.image_to_string(img, lang="eng+hin+ben")
            except pytesseract.TesseractError:
                t = pytesseract.image_to_string(img)
            return t, "tesseract", ""
        return data.decode("utf-8", "ignore"), "text", ""
    except ImportError as e:
        return "", "unavailable", f"OCR dependency missing: {e}"
    except Exception as e:  # noqa: BLE001
        return "", "error", str(e)
