import pymupdf4llm


def extract_text_from_pdf(pdf_path: str, document_type: str = "") -> str:
    """
    Extracts text from a PDF using pymupdf4llm.
    Falls back to OCR if no text is extracted or extraction fails.
    
    Args:
        pdf_path: Path to the PDF file
        document_type: Type of document (syllabus, pyqs, etc.) - for logging only
    
    Returns:
        str: Extracted text from the PDF
    """
    print(f"\n[PDF Extract] Processing: {pdf_path}")
    print(f"[PDF Extract] Document type: {document_type}")
    
    # Try pymupdf4llm first (fast, works for text-based PDFs)
    try:
        print("[PDF Extract] Attempting text extraction with pymupdf4llm...")
        markdown_text = pymupdf4llm.to_markdown(pdf_path)
        
        # Check if we got meaningful text
        if markdown_text and markdown_text.strip() and len(markdown_text.strip()) > 50:
            print(f"[PDF Extract] ✅ Successfully extracted {len(markdown_text)} characters")
            return markdown_text
        else:
            print("[PDF Extract] ⚠️ Text extraction returned empty or minimal content")
            print("[PDF Extract] Falling back to OCR...")
            
    except Exception as e:
        print(f"[PDF Extract] ⚠️ Text extraction failed: {e}")
        print("[PDF Extract] Falling back to OCR...")
    
    # Fallback to OCR (slower, works for scanned PDFs)
    try:
        from backend.services.input_analysis.OCR_Engine import extract_text_with_ocr
        print("[PDF Extract] Running OCR extraction...")
        ocr_text = extract_text_with_ocr(pdf_path, languages=['en'], gpu=False)
        
        if ocr_text and ocr_text.strip():
            print(f"[PDF Extract] ✅ OCR extracted {len(ocr_text)} characters")
            return ocr_text
        else:
            print("[PDF Extract] ⚠️ OCR returned empty content")
            return ""
            
    except Exception as e:
        print(f"[PDF Extract] ❌ OCR extraction failed: {e}")
        raise RuntimeError(f"PDF extraction failed (both text and OCR methods): {e}")


def process_pdf(pdf_path: str, document_type: str = "") -> str:
    """
    Process a PDF file and return extracted text.
    Alias for extract_text_from_pdf for backward compatibility.
    
    Args:
        pdf_path: Path to the PDF file
        document_type: Type of document (syllabus, pyqs, etc.)
    
    Returns:
        str: Extracted text from the PDF
    """
    return extract_text_from_pdf(pdf_path, document_type)


# Test code (uncomment to test standalone)
# if __name__ == "__main__":
#     text = extract_text_from_pdf(
#         r"C:\Users\Tejas\Desktop\Multi-Agent-Question-Paper-Generator\syllabus.pdf",
#         "syllabus"
#     )
#     print("\n--- Extracted Text Preview ---")
#     print(text[:500])
