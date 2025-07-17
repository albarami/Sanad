import json
import os
from pathlib import Path
from sentence_transformers import SentenceTransformer
import numpy as np
from tqdm import tqdm
import pickle

# Configuration
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

def load_chunks(processed_dir: Path):
    """
    Load all chunks from the processed directory.
    
    Args:
        processed_dir (Path): Directory containing the JSON chunk files.
        
    Returns:
        list[dict]: All chunks from all documents.
    """
    all_chunks = []
    
    for json_file in processed_dir.glob("*.json"):
        with open(json_file, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
            all_chunks.extend(chunks)
    
    return all_chunks

def build_embeddings(chunks, model):
    """
    Generate embeddings for all chunks.
    
    Args:
        chunks (list[dict]): List of chunk dictionaries.
        model: The sentence transformer model.
        
    Returns:
        np.ndarray: Array of embeddings.
    """
    texts = [chunk['text'] for chunk in chunks]
    print(f"Generating embeddings for {len(texts)} chunks...")
    
    embeddings = model.encode(
        texts, 
        batch_size=32, 
        show_progress_bar=True,
        convert_to_numpy=True
    )
    
    return embeddings

def save_index_data(chunks, embeddings, output_dir: Path):
    """
    Save the chunks and embeddings for later retrieval.
    
    Args:
        chunks (list[dict]): The chunk data.
        embeddings (np.ndarray): The embeddings.
        output_dir (Path): Directory to save the index data.
    """
    output_dir.mkdir(exist_ok=True)
    
    # Save chunks
    with open(output_dir / "chunks.json", 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    
    # Save embeddings
    np.save(output_dir / "embeddings.npy", embeddings)
    
    # Create category indices
    indices_by_category = {
        'official': [],
        'research': [],
        'all': list(range(len(chunks)))
    }
    
    for idx, chunk in enumerate(chunks):
        category = chunk.get('category', 'research')
        indices_by_category[category].append(idx)
    
    with open(output_dir / "category_indices.json", 'w') as f:
        json.dump(indices_by_category, f)
    
    print(f"Index data saved to {output_dir}")
    print(f"Total chunks: {len(chunks)}")
    print(f"Official chunks: {len(indices_by_category['official'])}")
    print(f"Research chunks: {len(indices_by_category['research'])}")

def main():
    # Set up paths
    project_root = Path(__file__).parent.parent
    processed_dir = project_root / "data" / "processed"
    index_dir = project_root / "data" / "index"
    
    # Load chunks
    chunks = load_chunks(processed_dir)
    print(f"Loaded {len(chunks)} chunks from {len(list(processed_dir.glob('*.json')))} documents")
    
    # Initialize model
    print(f"Loading embedding model: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)
    
    # Build embeddings
    embeddings = build_embeddings(chunks, model)
    
    # Save everything
    save_index_data(chunks, embeddings, index_dir)
    
    print("\nIndexing complete!")

if __name__ == "__main__":
    main() 