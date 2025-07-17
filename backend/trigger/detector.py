"""
Trigger Detector module that decides whether to use Sanad verification.
"""

import re
from typing import List
from sentence_transformers import SentenceTransformer
import numpy as np


class TriggerDetector:
    """
    Determines whether a query should trigger the Sanad verification process.
    Uses both keyword matching and semantic similarity.
    """
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize the trigger detector.
        
        Args:
            model_name (str): Name of the sentence transformer model.
        """
        self.model = SentenceTransformer(model_name)
        
        # Keywords that indicate need for verification
        self.verification_keywords = [
            # Legal/regulatory terms
            'law', 'legal', 'regulation', 'article', 'clause', 'provision',
            'قانون', 'مادة', 'نظام', 'لائحة',
            
            # Employment terms
            'employee', 'employer', 'worker', 'contract', 'termination',
            'عامل', 'موظف', 'عقد', 'إنهاء',
            
            # Rights and obligations
            'rights', 'obligations', 'duties', 'entitlement', 'compensation',
            'حقوق', 'واجبات', 'تعويض',
            
            # Procedural terms
            'procedure', 'process', 'requirement', 'deadline', 'period',
            'إجراء', 'متطلبات', 'مدة', 'فترة',
            
            # Economic/statistical terms requiring accuracy
            'gdp', 'growth rate', 'statistics', 'percentage', 'forecast',
            'نمو', 'إحصائيات', 'نسبة', 'توقعات',
            
            # Factual queries
            'how much', 'how many', 'what is the', 'when does', 'who can',
            'كم', 'متى', 'من يستطيع', 'ما هو'
        ]
        
        # Phrases that indicate need for verification
        self.verification_phrases = [
            'according to', 'as per', 'under the law', 'legally',
            'حسب القانون', 'وفقا', 'بموجب'
        ]
        
        # Reference queries for semantic similarity
        self.reference_queries = [
            "What does the law say about this?",
            "What are the legal requirements?",
            "What is the official procedure?",
            "What are the exact statistics?",
            "ما هو النص القانوني؟",
            "ما هي المتطلبات الرسمية؟"
        ]
        
        # Pre-encode reference queries
        self.reference_embeddings = self.model.encode(
            self.reference_queries, 
            convert_to_numpy=True
        )
        
        # Threshold for semantic similarity
        self.semantic_threshold = 0.72
        
    def use_sanad(self, query: str) -> bool:
        """
        Determine whether to use Sanad verification for the query.
        
        Args:
            query (str): The user's query.
            
        Returns:
            bool: True if Sanad verification should be used, False otherwise.
        """
        # Convert to lowercase for keyword matching
        query_lower = query.lower()
        
        # Check for exact keyword matches
        keyword_match = any(
            keyword in query_lower 
            for keyword in self.verification_keywords
        )
        
        if keyword_match:
            return True
        
        # Check for phrase matches
        phrase_match = any(
            phrase in query_lower 
            for phrase in self.verification_phrases
        )
        
        if phrase_match:
            return True
        
        # Check semantic similarity
        query_embedding = self.model.encode([query], convert_to_numpy=True)[0]
        
        # Calculate similarities with reference queries
        similarities = []
        for ref_embedding in self.reference_embeddings:
            similarity = np.dot(query_embedding, ref_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(ref_embedding)
            )
            similarities.append(similarity)
        
        max_similarity = max(similarities)
        
        return max_similarity > self.semantic_threshold
    
    def get_trigger_reason(self, query: str) -> str:
        """
        Get a human-readable reason for why the trigger was activated.
        
        Args:
            query (str): The user's query.
            
        Returns:
            str: Explanation of why Sanad was triggered.
        """
        query_lower = query.lower()
        
        # Check keywords
        matched_keywords = [
            keyword for keyword in self.verification_keywords 
            if keyword in query_lower
        ]
        
        if matched_keywords:
            return f"Query contains verification keywords: {', '.join(matched_keywords[:3])}"
        
        # Check phrases
        matched_phrases = [
            phrase for phrase in self.verification_phrases 
            if phrase in query_lower
        ]
        
        if matched_phrases:
            return f"Query contains verification phrases: {', '.join(matched_phrases)}"
        
        # Must be semantic similarity
        return "Query semantically similar to verification-requiring questions"


if __name__ == "__main__":
    # Test the trigger detector
    detector = TriggerDetector()
    
    test_queries = [
        # Should trigger
        "What are the working hours according to Qatar labor law?",
        "How much is the GDP growth rate?",
        "What is the legal procedure for termination?",
        "Tell me about employee rights",
        
        # Should not trigger
        "Hello, how are you?",
        "What is the weather today?",
        "Tell me a joke",
        "How to cook pasta?"
    ]
    
    print("Testing Trigger Detector:\n")
    for query in test_queries:
        should_trigger = detector.use_sanad(query)
        reason = detector.get_trigger_reason(query) if should_trigger else "No trigger"
        print(f"Query: {query}")
        print(f"Trigger: {should_trigger}")
        print(f"Reason: {reason}\n") 