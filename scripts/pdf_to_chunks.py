import json
import os
import re
from pathlib import Path

import fitz  # PyMuPDF
from tqdm import tqdm
from transformers import AutoTokenizer

# --- Configuration ---
TOKENIZER_NAME = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100


def get_pdf_files(source_dir: Path):
    """
    Recursively finds all PDF files in the source directory.

    Args:
        source_dir (Path): The directory to search for PDF files.

    Returns:
        list[Path]: A list of paths to the PDF files.
    """
    return list(source_dir.glob("**/*.pdf"))


def clean_text(text: str) -> str:
    """
    Cleans up the extracted text by removing excessive whitespace and correcting common OCR errors.

    Args:
        text (str): The text to clean.

    Returns:
        str: The cleaned text.
    """
    text = text.replace("-\n", "")  # De-hyphenate
    text = re.sub(r"\s+", " ", text)  # Collapse whitespace
    return text.strip()


def chunk_document(doc_id: str, text: str, tokenizer, category: str):
    """
    Splits a document's text into smaller chunks based on token count.

    Args:
        doc_id (str): The unique identifier for the document.
        text (str): The full text of the document.
        tokenizer: The tokenizer to use for splitting the text.
        category (str): The category of the document (e.g., 'official', 'research').

    Returns:
        list[dict]: A list of chunk dictionaries.
    """
    tokens = tokenizer.encode(text)
    chunks = []
    start = 0
    chunk_id_counter = 0
    while start < len(tokens):
        end = start + CHUNK_SIZE
        chunk_tokens = tokens[start:end]
        chunk_text = tokenizer.decode(chunk_tokens, skip_special_tokens=True)

        chunks.append(
            {
                "doc_id": doc_id,
                "chunk_id": f"{doc_id}-{chunk_id_counter}",
                "text": chunk_text,
                "category": category,
                "token_count": len(chunk_tokens),
            }
        )

        chunk_id_counter += 1
        if end >= len(tokens):
            break
        start += CHUNK_SIZE - CHUNK_OVERLAP

    return chunks


def process_pdfs(source_dir: Path, output_dir: Path):
    """
    Processes all PDFs in the source directory, chunks them, and saves them to the output directory.

    Args:
        source_dir (Path): The directory containing the source PDF files.
        output_dir (Path): The directory where the processed JSON chunks will be saved.
    """
    output_dir.mkdir(exist_ok=True)
    pdf_files = get_pdf_files(source_dir)
    tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_NAME)

    if not pdf_files:
        print(f"No PDF files found in {source_dir}")
        return

    print(f"Found {len(pdf_files)} PDF files to process.")

    for pdf_path in tqdm(pdf_files, desc="Processing PDFs"):
        doc_id = pdf_path.stem
        category = "research" if "TMO_research" in str(pdf_path) else "official"

        try:
            with fitz.open(pdf_path) as doc:
                full_text = ""
                for page in doc:
                    full_text += page.get_text() + "\n"

            cleaned_text = clean_text(full_text)
            document_chunks = chunk_document(doc_id, cleaned_text, tokenizer, category)

            output_filename = output_dir / f"{doc_id}.json"
            with open(output_filename, "w", encoding="utf-8") as f:
                json.dump(document_chunks, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"Error processing {pdf_path}: {e}")

    print(f"\nProcessing complete. Chunks saved to {output_dir}")


if __name__ == "__main__":
    # Assuming the script is run from the project root
    project_root = Path(__file__).parent.parent
    source_pdf_dir = project_root / "pdfs"
    processed_data_dir = project_root / "data" / "processed"

    process_pdfs(source_pdf_dir, processed_data_dir)
