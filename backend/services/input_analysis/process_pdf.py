import os
import pymupdf4llm


MIN_EXTRACTED_CHARS = 300


def _is_usable_text(text: str, min_chars: int = MIN_EXTRACTED_CHARS) -> bool:
    """Accept text only if it is long enough and not an extraction refusal."""
    if not text or not text.strip():
        return False

    cleaned = text.strip()
    lowered = cleaned.lower()

    refusal_markers = [
        "i'm unable to provide",
        "i am unable to provide",
        "can't provide",
        "cannot provide",
        "let me know how you'd like to proceed",
        "i can offer a summarized version",
    ]

    if any(marker in lowered for marker in refusal_markers):
        return False

    return len(cleaned) >= min_chars


def _extract_with_local_ocr(pdf_path: str) -> str:
    """Fallback OCR using local EasyOCR pipeline."""
    from backend.services.input_analysis.OCR_Engine import extract_text_with_ocr
    return extract_text_with_ocr(pdf_path)


# ── Gemini extraction ─────────────────────────────────────────────────────────

def _extract_with_gemini(pdf_path: str) -> str:
    """Upload PDF to Gemini Files API and extract all text."""
    from google import genai

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")

    client = genai.Client(api_key=api_key)

    print("[PDF Extract] Uploading PDF to Gemini Files API...")
    uploaded_file = client.files.upload(file=pdf_path)

    prompt = (
        "Extract all text from this PDF exactly as shown. "
        "Preserve line breaks, table structure and reading order. "
        "Return only the extracted text, no summary, no commentary."
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt, uploaded_file],
    )

    # Clean up the uploaded file to avoid hitting storage limits
    try:
        if uploaded_file.name:
            client.files.delete(name=uploaded_file.name)
    except Exception:
        pass

    return response.text or ""


# ── OpenAI extraction ─────────────────────────────────────────────────────────

def _extract_with_openai(pdf_path: str) -> str:
    """Upload PDF to OpenAI Files API and extract all text."""
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    client = OpenAI(api_key=api_key)

    print("[PDF Extract] Uploading PDF to OpenAI Files API...")
    with open(pdf_path, "rb") as f:
        uploaded_file = client.files.create(file=f, purpose="user_data")

    resp = client.responses.create(
        model="gpt-4o-mini",
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_file",
                        "file_id": uploaded_file.id,
                    },
                    {
                        "type": "input_text",
                        "text": (
                            "The user uploaded this PDF for OCR in their own workspace. "
                            "Transcribe the document into plain text for downstream parsing. "
                            "Preserve reading order, headings, question numbering, marks, and table rows/columns as text. "
                            "Do not summarize, explain, or redact. "
                            "Return only the extracted text content."
                        ),
                    },
                ],
            }
        ],
    )

    # Clean up the uploaded file
    try:
        client.files.delete(uploaded_file.id)
    except Exception:
        pass

    return resp.output_text or ""


# ── Main extraction logic ─────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_path: str, document_type: str = "") -> str:
    """
    Extracts text from a PDF using a three-tier strategy:
      1. pymupdf4llm  — fast, zero-cost, works for text-based PDFs
      2. Gemini       — AI OCR fallback for scanned/image PDFs
      3. OpenAI       — secondary fallback if Gemini fails (quota, API error, etc.)

    Args:
        pdf_path: Path to the PDF file
        document_type: Type of document (syllabus, pyqs, etc.) — for logging only

    Returns:
        str: Extracted text from the PDF
    """
    print(f"\n[PDF Extract] Processing: {pdf_path}")
    print(f"[PDF Extract] Document type: {document_type}")

    # ── Tier 1: pymupdf4llm (fast, text-based PDFs) ───────────────────────────
    try:
        print("[PDF Extract] Attempting text extraction with pymupdf4llm...")
        raw_markdown = pymupdf4llm.to_markdown(pdf_path)
        markdown_text = raw_markdown if isinstance(raw_markdown, str) else "\n".join(str(x) for x in raw_markdown)

        if _is_usable_text(markdown_text):
            print(f"[PDF Extract] ✅ pymupdf4llm extracted {len(markdown_text)} characters")
            return markdown_text

        print("[PDF Extract] ⚠️  pymupdf4llm returned minimal content — falling back to AI OCR")

    except Exception as e:
        print(f"[PDF Extract] ⚠️  pymupdf4llm failed: {e} — falling back to AI OCR")

    # ── Tier 2: Gemini ────────────────────────────────────────────────────────
    try:
        print("[PDF Extract] Trying Gemini OCR...")
        gemini_text = _extract_with_gemini(pdf_path)

        if _is_usable_text(gemini_text):
            print(f"[PDF Extract] ✅ Gemini extracted {len(gemini_text)} characters")
            return gemini_text

        print("[PDF Extract] ⚠️  Gemini returned minimal/refusal content — falling back to OpenAI")

    except Exception as e:
        print(f"[PDF Extract] ⚠️  Gemini OCR failed ({type(e).__name__}: {e}) — falling back to OpenAI")

    # ── Tier 3: OpenAI ────────────────────────────────────────────────────────
    try:
        print("[PDF Extract] Trying OpenAI OCR...")
        openai_text = _extract_with_openai(pdf_path)

        if _is_usable_text(openai_text):
            print(f"[PDF Extract] ✅ OpenAI extracted {len(openai_text)} characters")
            return openai_text

        print("[PDF Extract] ⚠️  OpenAI returned minimal/refusal content — trying local OCR engine")

    except Exception as e:
        print(f"[PDF Extract] ⚠️  OpenAI OCR failed: {e} — trying local OCR engine")

    # ── Tier 4: Local OCR Engine (EasyOCR) ──────────────────────────────────
    try:
        print("[PDF Extract] Trying local OCR engine...")
        local_text = _extract_with_local_ocr(pdf_path)
        if _is_usable_text(local_text):
            print(f"[PDF Extract] ✅ Local OCR extracted {len(local_text)} characters")
            return local_text

        print("[PDF Extract] ⚠️  Local OCR returned minimal/refusal content")
        return local_text or ""
    except Exception as e:
        print(f"[PDF Extract] ❌ Local OCR also failed: {e}")
        raise RuntimeError(
            "PDF extraction failed — all methods (pymupdf4llm, Gemini, OpenAI, Local OCR) exhausted. "
            f"Last error: {e}"
        )


def process_pdf(pdf_path: str, document_type: str = "") -> str:
    """
    Process a PDF file and return extracted text.
    Alias for extract_text_from_pdf for backward compatibility.
    """
    return extract_text_from_pdf(pdf_path, document_type)
