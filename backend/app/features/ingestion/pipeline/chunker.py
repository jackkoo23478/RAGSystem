def chunk_text (text : str , chunk_size : int = 500 , overlap : int = 50) -> list[str] :
    
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")
    
    packs = []
    start = 0 
    step = chunk_size - overlap
    
    while start < len(text):
        end = start + chunk_size
        pack = text[start:end].strip()
        if pack: 
            packs.append(pack)
        start += step   
    
    return packs

def chunk_pages(
    pages: list[tuple[int | None, str]],
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[tuple[int | None, str]]:
    result = []
    for page_number, text in pages:
        for piece in chunk_text(text, chunk_size, overlap):
            result.append((page_number, piece))
    return result