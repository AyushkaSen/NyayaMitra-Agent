"""Document & OCR Agent: extracts text, finds identifiers, validates format/checksum/expiry."""
from __future__ import annotations

from .. import tools


def run(text: str, file_bytes: bytes | None, filename: str, tool) -> dict:
    ocr_text, method, note = "", None, ""
    if file_bytes:
        ocr_text, method, note = tools.extract_text(file_bytes, filename)
        tool("ocr_extract", {"file": filename, "bytes": len(file_bytes)},
             {"method": method, "chars": len(ocr_text), "note": note or "ok"})
    combined = f"{text}\n{ocr_text}"
    findings = tools.validate_documents(combined)
    tool("validate_documents", {"chars_scanned": len(combined)},
         [f"{d['type']}: {d['status']}" for d in findings] or "no identifiers found")
    fields = tools.extract_fields(ocr_text or text)
    if fields:
        tool("extract_fields", {}, fields)
    return {"findings": findings, "fields": fields, "ocr_method": method, "ocr_note": note}
