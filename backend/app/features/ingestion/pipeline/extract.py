from pypdf import PdfReader


def extract_pages(file_path: str, file_type: str) -> list[tuple[int | None, str]]:
    if file_type == "txt":
        with open(file_path, "r", encoding="utf-8") as f:
            return [(None, f.read())]

    if file_type == "pdf":
        pdf_reader = PdfReader(file_path)
        texts = [page.extract_text() or "" for page in pdf_reader.pages]
        return [(number, text) for number, text in enumerate(texts, start=1)]

    raise ValueError(f"Unsupported file type: {file_type}")
        
