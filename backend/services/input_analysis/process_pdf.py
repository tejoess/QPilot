from docling.document_converter import DocumentConverter

def process_pdf(file_path: str):
    converter = DocumentConverter()  # uses GPU automatically if CUDA is available [web:3]
    result = converter.convert(file_path)
    #print(result)
    # Export the full document as markdown or text
    markdown_text = result.document.export_to_markdown()
    print(markdown_text[:1000])  # Print first 1000 characters of the markdown text
    print("\n--- Full Document Text ---")
    print(markdown_text[:1000])  # Print first 1000 characters

    # Save to file
    with open("extracted_syllabus.txt", "w", encoding="utf-8") as f:
        f.write(markdown_text)
        
    print("\n✅ Syllabus extracted and saved to 'extracted_syllabus.txt'")

    return markdown_text

#process_pdf(r"C:\Users\Tejas\Desktop\Multi-Agent-Question-Paper-Generator\syllabus.pdf")