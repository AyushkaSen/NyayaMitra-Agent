# NyayaMitra-Agent


Multi-agent assistant for Indian MSMEs, street vendors and citizens: checks documents, matches government
schemes and compliance duties, and drafts forms and letters. Built for the BharatAgentic Hackathon
(LegalTech & Compliance / Citizen & GovTech).

## Agent flow

```
Understand -> Reason -> Plan -> Use tools -> Act -> Deliver      (LangGraph StateGraph)
                                   |            |
                 Document & OCR Agent    Action & Workflow Agent
                 Scheme & Compliance Agent
```

| Stage | What happens |
|---|---|
| Understand | Script-based language detection (Devanagari, Bengali, Tamil, Telugu and more, plus romanised Hindi). Multilingual keyword lexicon builds a profile: business type, state, turnover, employees, women / SC-ST, existing registrations, grievance type. If `ANTHROPIC_API_KEY` is set, an LLM fills gaps. |
| Reason | Lists needs (Udyam, FSSAI, vending certificate, credit, grievance route) and states assumptions. |
| Plan | Decides which sub-agents to run. The Document agent runs only if a file or identifier is present. |
| Use tools | **Document & OCR Agent**: Tesseract / pypdf text extraction, then format, checksum and expiry validation for Udyam, GSTIN (with check digit), PAN, Aadhaar-format (Verhoeff, masked) and FSSAI. Valid registrations feed back into the profile. **Scheme & Compliance Agent**: TF-IDF vector retrieval over `app/data/schemes.json` plus explicit eligibility rules. |
| Act | Prioritised roadmap, pre-filled Udyam / SVANidhi sheets, and draft letters (MSMED Act delayed-payment notice, Town Vending Committee application, consumer notice, CPGRAMS text). With an API key, letters are also translated into the user's language. |
| Deliver | Result JSON rendered as tabs, with a disclaimer. |

The UI streams every step and tool call live over Server-Sent Events.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# OCR needs the tesseract binary: sudo apt install tesseract-ocr tesseract-ocr-hin tesseract-ocr-ben
uvicorn app.main:app --reload --port 8000
# open http://localhost:8000
```

## Run with Docker

```bash
docker build -t nyayamitra-agent .
docker run --rm -p 8000:8000 nyayamitra-agent
# optional LLM assist and translation:
docker run --rm -p 8000:8000 -e ANTHROPIC_API_KEY=sk-... nyayamitra-agent
```

## Test

```bash
pip install pytest httpx && NYAYA_PACE=0 pytest -q tests
curl -s -X POST localhost:8000/api/run_sync -F 'text=I sell tea on a handcart in Kolkata, need a loan' | python -m json.tool | head -40
```

## Files

```
app/main.py              FastAPI, SSE streaming, static UI
app/graph.py             LangGraph orchestration (falls back to a sequential loop if langgraph is missing)
app/agents/              document_agent, scheme_agent, action_agent
app/tools.py             language detection, profile extraction, validators, OCR
app/vector_index.py      dependency-free TF-IDF index (swap for Chroma / FAISS)
app/data/schemes.json    16 central / state / municipal schemes and compliance items
app/llm.py               optional Anthropic layer
static/index.html        Tailwind UI with live trace
agent.yaml               aiKart-style manifest template
```

## Limits to state in your demo

- Document checks verify format and checksum only. They do not query Udyam, GST or FSSAI registries.
- Scheme amounts, limits and URLs in `schemes.json` were written from general knowledge. Verify each against the official portal before the demo and update `_meta.last_reviewed`.
- `agent.yaml` follows a common manifest layout. Rename keys to match the official aiKart schema.
- The rule-based language layer covers common phrasing, not every dialect. The LLM option improves this.
- Not legal advice.

## Extending

- Add a scheme: append an entry to `schemes.json` (`kw` can hold Hindi, Bengali and other-language keywords; `rules` drives eligibility).
- Add state schemes: new entries with `rules.segments_any` and a state check in `scheme_agent.evaluate`.
- Better retrieval: replace `TfidfIndex` with a multilingual embedding model behind the same `search(query, k)`.
=======
navigating complex legal/government compliance and documentation for small businesses or citizens.
>>>>>>> 090805e54200d95520e033b45f2ba0da423dbbae
