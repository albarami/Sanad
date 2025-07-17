"""
Simple retriever module that works without FAISS.
This is a temporary implementation for Windows development.
Will be replaced with FAISS-GPU when running on WSL2.
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer


class SimpleRetriever:
    """
    A simple retriever that uses cosine similarity for searching.
    This is a temporary implementation that doesn't require FAISS.
    """
    
    def __init__(self, index_dir: Path, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize the retriever with pre-built index data.
        
        Args:
            index_dir (Path): Directory containing the index files.
            model_name (str): Name of the sentence transformer model.
        """
        self.index_dir = index_dir
        self.model = SentenceTransformer(model_name)
        
        # Load chunks
        with open(index_dir / "chunks.json", 'r', encoding='utf-8') as f:
            self.chunks = json.load(f)
        
        # Load embeddings
        self.embeddings = np.load(index_dir / "embeddings.npy")
        
        # Load category indices
        with open(index_dir / "category_indices.json", 'r') as f:
            self.category_indices = json.load(f)
        
        print(f"Loaded {len(self.chunks)} chunks with embeddings")
    
    def search(self, query: str, k: int = 5, category: Optional[str] = None) -> List[Dict]:
        """
        Search for the most similar chunks to the query.
        
        Args:
            query (str): The search query.
            k (int): Number of results to return.
            category (str, optional): Filter by category ('official', 'research', or None for all).
            
        Returns:
            List[Dict]: List of the most similar chunks with scores.
        """
        # Encode the query
        query_embedding = self.model.encode([query], convert_to_numpy=True)[0]
        
        # Determine which indices to search
        if category and category in self.category_indices:
            indices = self.category_indices[category]
        else:
            indices = self.category_indices['all']
        
        # Calculate cosine similarities
        similarities = []
        for idx in indices:
            chunk_embedding = self.embeddings[idx]
            # Cosine similarity
            similarity = np.dot(query_embedding, chunk_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(chunk_embedding)
            )
            similarities.append((idx, similarity))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Get top k results
        results = []
        for idx, score in similarities[:k]:
            result = self.chunks[idx].copy()
            result['score'] = float(score)
            result['distance'] = float(1 - score)  # Convert similarity to distance
            results.append(result)
        
        return results
    
    def route(self, query: str) -> str:
        """
        Determine which category of documents to search based on the query.
        
        Args:
            query (str): The search query.
            
        Returns:
            str: The category to search ('official', 'research', or 'all').
        """
        # Simple keyword-based routing for now
        query_lower = query.lower()
        
        official_keywords = ['law', 'قانون', 'legal', 'regulation', 'article', 'مادة', 
                           'employee', 'employer', 'contract', 'عقد', 'عمل', 'موظف']
        research_keywords = ['economy', 'gdp', 'growth', 'analysis', 'trend', 'forecast',
                           'market', 'sector', 'statistics', 'data']
        
        official_score = sum(1 for keyword in official_keywords if keyword in query_lower)
        research_score = sum(1 for keyword in research_keywords if keyword in query_lower)
        
        if official_score > research_score:
            return 'official'
        elif research_score > official_score:
            return 'research'
        else:
            return 'all'


if __name__ == "__main__":
    # Test the retriever
    project_root = Path(__file__).parent.parent.parent  # Go up 3 levels from backend/retrieval/simple_retriever.py
    index_dir = project_root / "data" / "index"
    
    retriever = SimpleRetriever(index_dir)
    
    # Test queries
    test_queries = [
        "What are the working hours according to Qatar labor law?",
        "What is the GDP growth rate of Qatar?",
        "Employee termination procedures"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        category = retriever.route(query)
        print(f"Routed to category: {category}")
        
        results = retriever.search(query, k=3, category=category)
        for i, result in enumerate(results):
            print(f"\n{i+1}. Score: {result['score']:.3f}")
            print(f"   Doc: {result['doc_id']}")
            print(f"   Text: {result['text'][:150]}...") 