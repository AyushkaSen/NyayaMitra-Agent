from fastapi.testclient import TestClient
from app.main import app
from app import tools

c = TestClient(app)


def run(text):
    r = c.post("/api/run_sync", data={"text": text})
    assert r.status_code == 200, r.text
    return r.json()["result"]


def test_validators():
    base = "23412341234"
    good = next(base + str(d) for d in range(10) if tools.verhoeff_ok(base + str(d)))
    assert tools.verhoeff_ok(good) and not tools.verhoeff_ok(good[:-1] + str((int(good[-1]) + 1) % 10))
    assert tools.gstin_checksum_ok("27AAPFU0939F1ZV")  # well-known sample GSTIN


def test_tea_stall():
    r = run("I run a tea stall on a handcart near Howrah, Kolkata. Sales about 3 lakh a year. Need a small loan. I am a woman.")
    ids = {s["id"] for s in r["schemes"]}
    assert {"pm_svanidhi", "fssai", "udyam", "vending_certificate"} <= ids
    assert r["profile"]["turnover"] == 300000 and r["profile"]["state"] == "West Bengal"


def test_hindi_and_bengali():
    assert run("मैं दिल्ली में ठेले पर सब्ज़ी बेचता हूँ, लोन चाहिए")["language"]["code"] == "hi"
    r = run("আমি কলকাতায় খাবারের দোকান চালাই। বছরে ১৫ লাখ টাকার বিক্রি। উদ্যম রেজিস্ট্রেশন দরকার।")
    assert r["language"]["code"] == "bn" and r["profile"]["turnover"] == 1500000


def test_payment_letter():
    r = run("A buyer owes my manufacturing unit ₹2.5 lakh. Invoice dated 12/05/2026. Udyam UDYAM-MH-26-0012345")
    assert r["letters"] and "MSMED" in r["letters"][0]["body"] and "26 June 2026" in r["letters"][0]["body"]
    assert any(d["type"] == "Udyam Registration" and d["status"] == "valid_format" for d in r["documents"])


def test_stream_and_empty():
    r = c.post("/api/run", data={"text": "I have a kirana shop"})
    assert "event" not in r.text and '"type": "final"' in r.text
    assert c.post("/api/run_sync", data={"text": ""}).status_code == 400
