"""
FAISS-based retrieval system for Sanad v2.

This module implements the FAISSRetriever class that loads a pre-built FAISS index
and performs vector similarity search for document retrieval.
"""

import json
import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple

import faiss
import numpy as np
from openai import OpenAI

from backend.db.models import Passage

logger = logging.getLogger(__name__)


class FAISSRetriever:
    """
    FAISS-based document retriever for semantic search.

    Loads a pre-built FAISS index and chunk metadata to perform
    vector similarity search against the document corpus.
    """

    def __init__(
        self, index_path: str = "data/index", openai_client: Optional[OpenAI] = None
    ):
        """
        Initialize the FAISS retriever.

        Args:
            index_path: Path to directory containing FAISS index and metadata
            openai_client: OpenAI client for generating query embeddings
        """
        self.index_path = Path(index_path)
        self.openai_client = openai_client or OpenAI()

        # Initialize components
        self.index: Optional[faiss.Index] = None
        self.chunks: List[dict] = []
        self.category_indices: dict = {}

        # Load the index and metadata
        self._load_index()
        self._load_chunks()
        self._load_category_indices()

        logger.info(f"✅ FAISSRetriever initialized with {len(self.chunks)} chunks")

    def _load_index(self) -> None:
        """Load the FAISS index from disk."""
        index_file = self.index_path / "faiss.index"

        if not index_file.exists():
            raise FileNotFoundError(f"FAISS index not found at {index_file}")

        self.index = faiss.read_index(str(index_file))
        logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors")

    def _load_chunks(self) -> None:
        """Load chunk metadata from JSON file."""
        chunks_file = self.index_path / "chunks.json"

        if not chunks_file.exists():
            raise FileNotFoundError(f"Chunks metadata not found at {chunks_file}")

        with open(chunks_file, "r", encoding="utf-8") as f:
            self.chunks = json.load(f)

        logger.info(f"Loaded {len(self.chunks)} chunk metadata entries")

    def _load_category_indices(self) -> None:
        """Load category index mappings."""
        category_file = self.index_path / "category_indices.json"

        if category_file.exists():
            with open(category_file, "r", encoding="utf-8") as f:
                self.category_indices = json.load(f)
            logger.info(
                f"Loaded category indices for {len(self.category_indices)} categories"
            )
        else:
            logger.warning(
                "No category indices found, using full index for all queries"
            )

    def _get_query_embedding(self, query: str) -> np.ndarray:
        """
        Generate embedding for the query using OpenAI.

        Args:
            query: The search query

        Returns:
            Query embedding as numpy array
        """
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small", input=query
            )
            embedding = np.array(response.data[0].embedding, dtype=np.float32)
            return embedding.reshape(1, -1)  # FAISS expects 2D array
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            raise

    def retrieve(
        self,
        query: str,
        k: int = 5,
        category: Optional[str] = None,
        score_threshold: float = 0.0,
    ) -> List[Passage]:
        """
        Retrieve the most relevant passages for a query.

        Args:
            query: The search query
            k: Number of results to return
            category: Optional category filter
            score_threshold: Minimum similarity score threshold

        Returns:
            List of Passage objects with relevance scores
        """
        if not self.index:
            raise RuntimeError("FAISS index not loaded")

        # Generate query embedding
        query_embedding = self._get_query_embedding(query)

        # Perform similarity search
        distances, indices = self.index.search(query_embedding, k)

        # Convert to passages
        passages = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            if idx == -1:  # FAISS returns -1 for empty results
                continue

            # Convert distance to similarity score (higher is better)
            similarity_score = 1.0 / (1.0 + distance)

            if similarity_score < score_threshold:
                continue

            chunk = self.chunks[idx]

            passage = Passage(
                chunk_id=f"chunk_{idx}",
                content=chunk["content"],
                source=chunk.get("source", "unknown"),
                category=chunk.get("category", "general"),
                distance=float(distance),
                metadata=chunk.get("metadata", {}),
            )

            passages.append(passage)

        logger.info(f"Retrieved {len(passages)} passages for query: {query[:50]}...")
        return passages

    def get_stats(self) -> dict:
        """
        Get retriever statistics.

        Returns:
            Dictionary with retriever statistics
        """
        return {
            "total_chunks": len(self.chunks),
            "index_size": self.index.ntotal if self.index else 0,
            "categories": (
                list(self.category_indices.keys()) if self.category_indices else []
            ),
            "index_path": str(self.index_path),
        }
