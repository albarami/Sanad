"""
Data processing script for Sanad v2.

This script processes source documents, chunks them, generates embeddings,
and builds a FAISS index for semantic search.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import faiss
import numpy as np
from openai import OpenAI

# Add backend to path for imports
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from core.config import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Processes documents and builds FAISS index for retrieval.
    """

    def __init__(self):
        """Initialize the document processor."""
        self.config = get_config()
        self.openai_client = OpenAI()

        # Paths
        self.data_dir = Path("data")
        self.processed_dir = self.data_dir / "processed"
        self.index_dir = self.data_dir / "index"

        # Create directories
        self.index_dir.mkdir(parents=True, exist_ok=True)

        # Processing parameters
        self.chunk_size = 500  # tokens
        self.chunk_overlap = 100  # tokens
        self.embedding_model = "text-embedding-3-small"

        logger.info("✅ DocumentProcessor initialized")

    def load_processed_documents(self) -> List[Dict[str, Any]]:
        """
        Load all processed documents from the processed directory.

        Returns:
            List of document dictionaries
        """
        documents = []

        if not self.processed_dir.exists():
            logger.warning(f"Processed directory not found: {self.processed_dir}")
            return documents

        for json_file in self.processed_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    doc_data = json.load(f)

                # Ensure document has required fields
                if isinstance(doc_data, dict) and "content" in doc_data:
                    doc_data["source"] = json_file.stem
                    documents.append(doc_data)
                elif isinstance(doc_data, list):
                    # Handle list of documents
                    for item in doc_data:
                        if isinstance(item, dict) and "content" in item:
                            item["source"] = json_file.stem
                            documents.append(item)

                logger.info(f"Loaded document: {json_file.name}")

            except Exception as e:
                logger.error(f"Failed to load {json_file}: {e}")

        logger.info(f"Loaded {len(documents)} documents total")
        return documents

    def chunk_text(
        self, text: str, source: str, category: str = "general"
    ) -> List[Dict[str, Any]]:
        """
        Chunk text into smaller pieces for embedding.

        Args:
            text: The text to chunk
            source: Source document name
            category: Document category

        Returns:
            List of chunk dictionaries
        """
        # Simple word-based chunking (can be improved with proper tokenization)
        words = text.split()
        chunks = []

        # Approximate tokens per word (rough estimate)
        words_per_chunk = self.chunk_size // 1.3  # Rough conversion
        overlap_words = self.chunk_overlap // 1.3

        for i in range(0, len(words), int(words_per_chunk - overlap_words)):
            chunk_words = words[i : i + int(words_per_chunk)]
            chunk_text = " ".join(chunk_words)

            if len(chunk_text.strip()) > 50:  # Skip very short chunks
                chunks.append(
                    {
                        "content": chunk_text,
                        "source": source,
                        "category": category,
                        "chunk_index": len(chunks),
                        "metadata": {
                            "word_count": len(chunk_words),
                            "char_count": len(chunk_text),
                        },
                    }
                )

        return chunks

    def generate_embeddings(self, chunks: List[Dict[str, Any]]) -> np.ndarray:
        """
        Generate embeddings for all chunks.

        Args:
            chunks: List of chunk dictionaries

        Returns:
            Numpy array of embeddings
        """
        logger.info(f"Generating embeddings for {len(chunks)} chunks...")

        # Extract text content
        texts = [chunk["content"] for chunk in chunks]

        # Generate embeddings in batches
        batch_size = 100
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]

            try:
                response = self.openai_client.embeddings.create(
                    model=self.embedding_model, input=batch_texts
                )

                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)

                logger.info(
                    f"Generated embeddings for batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}"
                )

            except Exception as e:
                logger.error(
                    f"Failed to generate embeddings for batch {i//batch_size + 1}: {e}"
                )
                raise

        embeddings_array = np.array(all_embeddings, dtype=np.float32)
        logger.info(
            f"✅ Generated {embeddings_array.shape[0]} embeddings of dimension {embeddings_array.shape[1]}"
        )

        return embeddings_array

    def build_faiss_index(self, embeddings: np.ndarray) -> faiss.Index:
        """
        Build FAISS index from embeddings.

        Args:
            embeddings: Numpy array of embeddings

        Returns:
            FAISS index
        """
        logger.info("Building FAISS index...")

        # Create index (using L2 distance)
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)

        # Add embeddings to index
        index.add(embeddings)

        logger.info(f"✅ Built FAISS index with {index.ntotal} vectors")
        return index

    def save_index_and_metadata(
        self, index: faiss.Index, chunks: List[Dict[str, Any]]
    ) -> None:
        """
        Save FAISS index and chunk metadata to disk.

        Args:
            index: FAISS index
            chunks: List of chunk dictionaries
        """
        # Save FAISS index
        index_file = self.index_dir / "faiss.index"
        faiss.write_index(index, str(index_file))
        logger.info(f"Saved FAISS index to {index_file}")

        # Save chunk metadata
        chunks_file = self.index_dir / "chunks.json"
        with open(chunks_file, "w", encoding="utf-8") as f:
            json.dump(chunks, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved chunk metadata to {chunks_file}")

        # Save embeddings (optional, for debugging)
        embeddings_file = self.index_dir / "embeddings.npy"
        embeddings = faiss.vector_to_array(index.get_xb()).reshape(index.ntotal, -1)
        np.save(embeddings_file, embeddings)
        logger.info(f"Saved embeddings to {embeddings_file}")

        # Create category indices
        category_indices = {}
        for i, chunk in enumerate(chunks):
            category = chunk.get("category", "general")
            if category not in category_indices:
                category_indices[category] = []
            category_indices[category].append(i)

        category_file = self.index_dir / "category_indices.json"
        with open(category_file, "w", encoding="utf-8") as f:
            json.dump(category_indices, f, indent=2)
        logger.info(f"Saved category indices to {category_file}")

    def process_all(self) -> None:
        """
        Main processing pipeline: load documents, chunk, embed, and index.
        """
        logger.info("🚀 Starting document processing pipeline...")

        # Load documents
        documents = self.load_processed_documents()
        if not documents:
            logger.error("No documents found to process")
            return

        # Chunk all documents
        all_chunks = []
        for doc in documents:
            content = doc.get("content", "")
            source = doc.get("source", "unknown")
            category = doc.get("category", "general")

            chunks = self.chunk_text(content, source, category)
            all_chunks.extend(chunks)

        logger.info(f"Created {len(all_chunks)} chunks from {len(documents)} documents")

        # Generate embeddings
        embeddings = self.generate_embeddings(all_chunks)

        # Build FAISS index
        index = self.build_faiss_index(embeddings)

        # Save everything
        self.save_index_and_metadata(index, all_chunks)

        logger.info("✅ Document processing pipeline completed successfully!")

        # Print summary
        print(f"\n📊 Processing Summary:")
        print(f"Documents processed: {len(documents)}")
        print(f"Chunks created: {len(all_chunks)}")
        print(f"Embeddings generated: {embeddings.shape[0]}")
        print(f"Index dimension: {embeddings.shape[1]}")
        print(f"Index saved to: {self.index_dir}")


def main():
    """Main entry point."""
    processor = DocumentProcessor()
    processor.process_all()


if __name__ == "__main__":
    main()
