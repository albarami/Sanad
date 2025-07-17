"""
Base agent class for the Sanad verification system.
All verification agents inherit from this base class.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple
from pydantic import BaseModel, Field
from loguru import logger


class Passage(BaseModel):
    """A text passage retrieved from the document corpus."""
    doc_id: str
    chunk_id: str
    text: str
    category: str
    score: float = Field(ge=0.0, le=1.0)
    distance: float = Field(ge=0.0)


class AgentInput(BaseModel):
    """Input data for an agent."""
    question: str
    draft_answer: str
    passages: List[Passage]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentScore(BaseModel):
    """Score and explanation from an agent."""
    score: float = Field(ge=0.0, le=1.0)
    explanation: str
    confidence: float = Field(ge=0.0, le=1.0)
    agent_name: str


class BaseAgent(ABC):
    """
    Abstract base class for all verification agents.
    Each agent evaluates a specific aspect of answer quality.
    """
    
    def __init__(self, name: str):
        """
        Initialize the base agent.
        
        Args:
            name: Name of the agent
        """
        self.name = name
        logger.info(f"Initialized {self.name} agent")
    
    @abstractmethod
    async def evaluate(self, input_data: AgentInput) -> AgentScore:
        """
        Evaluate the draft answer based on the agent's specific criteria.
        
        Args:
            input_data: Input containing question, draft answer, and passages
            
        Returns:
            AgentScore with score and explanation
        """
        pass
    
    def evaluate_sync(self, input_data: AgentInput) -> AgentScore:
        """
        Synchronous wrapper for the evaluate method.
        
        Args:
            input_data: Input containing question, draft answer, and passages
            
        Returns:
            AgentScore with score and explanation
        """
        import asyncio
        return asyncio.run(self.evaluate(input_data))
    
    def _extract_citations(self, text: str) -> List[str]:
        """
        Extract citations from text.
        
        Args:
            text: Text to extract citations from
            
        Returns:
            List of citation identifiers
        """
        import re
        # Look for patterns like [1], [doc_id], etc.
        citations = re.findall(r'\[([^\]]+)\]', text)
        return citations
    
    def _calculate_overlap(self, text1: str, text2: str) -> float:
        """
        Calculate the overlap between two texts using token overlap.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Overlap score between 0 and 1
        """
        # Simple token-based overlap
        tokens1 = set(text1.lower().split())
        tokens2 = set(text2.lower().split())
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _is_factual_claim(self, text: str) -> bool:
        """
        Determine if text contains a factual claim.
        
        Args:
            text: Text to analyze
            
        Returns:
            True if text appears to contain factual claims
        """
        # Keywords that often indicate factual claims
        factual_indicators = [
            'is', 'are', 'was', 'were', 'has', 'have', 'must', 'shall',
            'requires', 'states', 'specifies', 'according to', 'based on',
            '%', 'percent', 'number', 'amount', 'rate', 'ratio',
            'يجب', 'يكون', 'وفقا', 'حسب', 'نسبة'
        ]
        
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in factual_indicators) 