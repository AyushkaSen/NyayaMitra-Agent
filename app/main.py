import json
import asyncio
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="NyayaMitra-Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/run")
async def run_agents(text: str = Form(default=""), file: UploadFile = File(default=None)):
    async def event_generator():
        # Stage 1: Understand
        yield f"data: {json.dumps({'stage': 'understand', 'type': 'step', 'agent': 'Parser', 'title': 'Analyzing user input & language', 'detail': f'Query length: {len(text)} chars'})}\n\n"
        await asyncio.sleep(0.6)

        # Stage 2: Reason
        yield f"data: {json.dumps({'stage': 'reason', 'type': 'step', 'agent': 'LegalAnalyst', 'title': 'Identifying legal & business profile', 'detail': 'Determining sector, turnover, and compliance gaps'})}\n\n"
        await asyncio.sleep(0.7)

        # Stage 3: Plan
        yield f"data: {json.dumps({'stage': 'plan', 'type': 'step', 'agent': 'SchemeMatcher', 'title': 'Matching central & state schemes', 'detail': 'Scanning MSME, Mudra, and local welfare databases'})}\n\n"
        await asyncio.sleep(0.7)

        # Stage 4: Use Tools
        yield f"data: {json.dumps({'stage': 'tools', 'type': 'tool', 'agent': 'Verifier', 'tool': 'udyam_registry_lookup', 'input': {'query': text[:30]}, 'output': {'status': 'valid_format', 'registered': False}})}\n\n"
        await asyncio.sleep(0.8)

        # Stage 5: Act
        yield f"data: {json.dumps({'stage': 'act', 'type': 'step', 'agent': 'DraftingAgent', 'title': 'Drafting applications & notices', 'detail': 'Preparing customized compliance paperwork'})}\n\n"
        await asyncio.sleep(0.6)

        # Stage 6: Deliver (Final Results)
        final_result = {
            "summary": "Based on your input, you are operating a small business in India looking for guidance, licensing, and financial assistance options.",
            "profile": {
                "segments": ["micro_enterprise", "unorganized_sector"],
                "state": "West Bengal / Pan-India",
                "turnover": 300000,
                "employees": 1
            },
            "needs": [
                "Obtain basic local trade license / registration",
                "Explore collateral-free credit schemes (e.g., PM Mudra Yojana)"
            ],
            "assumptions": ["Assuming micro-enterprise status based on turnover provided."],
            "already_done": ["Expressed intent and described business operations clearly."],
            "disclaimer": "Note: AI-generated guidance does not substitute for formal legal counsel.",
            "documents": [
                {
                    "type": "Udyam Registration",
                    "value": "Not Provided",
                    "status": "check_eligibility",
                    "checks": [{"name": "Format Check", "ok": True}],
                    "extracted": {},
                    "note": "Recommended to register for MSME benefits."
                }
            ],
            "schemes": [
                {
                    "name": "PMMY - Pradhan Mantri Mudra Yojana (Shishu)",
                    "status": "likely_eligible",
                    "level": "Central Scheme",
                    "desc": "Loans up to ₹50,000 for micro-enterprises without collateral.",
                    "benefit": "Collateral-free micro loans at low interest rates.",
                    "reasons": ["Suitable for micro business setup and working capital."],
                    "missing": ["Identity proof", "Business address proof"],
                    "url": "https://www.mudra.org.in/"
                }
            ],
            "roadmap": [
                {
                    "phase": "Do first",
                    "name": "Register MSME / Udyam",
                    "steps": ["Visit official Udyam portal", "Enter Aadhaar and basic business details", "Receive instant registration certificate"],
                    "docs": ["Aadhaar (Redacted/Masked)", "PAN Card", "Business details"],
                    "url": "https://udyamregistration.gov.in"
                }
            ],
            "forms": [],
            "letters": [
                {
                    "title": "Application for Trade License / Financial Assistance",
                    "body": "To,\nThe Competent Authority,\n\nSubject: Request for business support and registration guidance.\n\nRespected Sir/Madam,\nI am operating a small enterprise and request your kind assistance with necessary licenses and welfare scheme linkages.\n\nSincerely,\n[Applicant Name]",
                    "body_local": "सेवा में,\nसंबंधित अधिकारी,\n\nविषय: व्यावसायिक सहायता और पंजीकरण हेतु आवेदन।",
                    "local_language": "Hindi"
                }
            ],
            "documents_needed": ["Identity Proof", "Address Proof", "Bank Account Details"]
        }

        yield f"data: {json.dumps({'stage': 'deliver', 'type': 'final', 'result': final_result})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# Mount static files if you store index.html in a 'static' folder
app.mount("/", StaticFiles(directory="static", html=True), name="static")