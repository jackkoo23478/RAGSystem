from pypdf import PdfReader


def extract_text(file_path:str , file_type : str) -> str :
    if file_type == "txt":
        with open(file_path , "r",encoding="utf-8") as f:
            return f.read()
    
    if file_type == "pdf":
        pdf_reader = PdfReader(file_path)
        pages = [page.extract_text() or "" for page in pdf_reader.pages]
        return "\n".join(pages)
    
    raise ValueError(f"Unsupported file type: {file_type}")