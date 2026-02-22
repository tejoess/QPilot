# from docling.document_converter import DocumentConverter

# def process_pdf(file_path: str, document_type: str):
#     converter = DocumentConverter()  # uses GPU automatically if CUDA is available [web:3]
#     result = converter.convert(file_path)
#     #print(result)
#     # Export the full document as markdown or text
#     markdown_text = result.document.export_to_markdown()
#     print(markdown_text[:1000])  # Print first 1000 characters of the markdown text
#     print("\n--- Full Document Text ---")
#     print(markdown_text[:1000])  # Print first 1000 characters

#     # Save to file
#     with open("extracted_syllabus.txt", "w", encoding="utf-8") as f:
#         f.write(markdown_text)
        
#     print("\n✅ Syllabus extracted and saved to 'extracted_syllabus.txt'")

#     return markdown_text



import pymupdf4llm

def extract_text_from_pdf(pdf_path: str, document_type: str) -> str:
    """
    Extracts text from a PDF using pymupdf4llm and returns it as a single string.
    """
    try:
        markdown_text = pymupdf4llm.to_markdown(pdf_path)
        return markdown_text
    except Exception as e:
        raise RuntimeError(f"PDF extraction failed: {e}")

# text = extract_text_from_pdf(r"C:\Users\Tejas\Desktop\Multi-Agent-Question-Paper-Generator\syllabus.pdf")
# print(text[:1000])  # Print first 1000 characters of the extracted text

# if not text:
#     print("No text extracted from the PDF.")
#     import pymupdf.layout
#     import pymupdf4llm
#     doc = pymupdf.open(r"C:\Users\Tejas\Desktop\AAI syllabus.pdf")
#     from pymupdf4llm.ocr import rapidtess_api

#     md = pymupdf4llm.to_markdown(
#         doc,
#         ocr_function=rapidtess_api.exec_ocr,
#         force_ocr=True
#     )
#     print(md)