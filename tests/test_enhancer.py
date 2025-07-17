"""
Unit tests for the ResponseEnhancer module.
Tests enhancement logic, threshold behavior, and integration with agents.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, List

# Import the modules to test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from core.enhancer import ResponseEnhancer, EnhancementRequest, EnhancementResponse
from agents.base import AgentScore, Passage


class TestResponseEnhancer:
    """Test suite for ResponseEnhancer class."""
    
    @pytest.fixture
    def sample_passages(self) -> List[Passage]:
        """Create sample passages for testing."""
        return [
            Passage(
                text="The five daily prayers (Salah) are obligatory for all Muslims.",
                doc_id="hadith_001",
                chunk_id="chunk_001",
                category="religious",
                distance=0.1,
                score=0.9,
                metadata={"source": "Sahih Bukhari"}
            ),
            Passage(
                text="Prayer times are determined by the position of the sun.",
                doc_id="fiqh_002",
                chunk_id="chunk_002",
                category="religious",
                distance=0.2,
                score=0.8,
                metadata={"source": "Islamic Jurisprudence"}
            ),
            Passage(
                text="Wudu (ablution) is required before performing prayer.",
                doc_id="hadith_003",
                chunk_id="chunk_003",
                category="religious",
                distance=0.15,
                score=0.85,
                metadata={"source": "Sahih Muslim"}
            )
        ]
    
    @pytest.fixture
    def sample_agent_scores(self) -> Dict[str, AgentScore]:
        """Create sample agent scores for testing."""
        return {
            "precision": AgentScore(
                score=0.6,
                explanation="Answer lacks specific details about prayer requirements",
                confidence=0.8,
                agent_name="precision"
            ),
            "provenance": AgentScore(
                score=0.5,
                explanation="Missing source citations for Islamic rulings",
                confidence=0.9,
                agent_name="provenance"
            ),
            "domain": AgentScore(
                score=0.7,
                explanation="Good use of Islamic terminology",
                confidence=0.7,
                agent_name="domain"
            ),
            "integrity": AgentScore(
                score=0.8,
                explanation="Logically consistent answer",
                confidence=0.8,
                agent_name="integrity"
            )
        }
    
    @pytest.fixture
    def enhancement_request(self, sample_passages, sample_agent_scores) -> EnhancementRequest:
        """Create a sample enhancement request."""
        return EnhancementRequest(
            question="What are the requirements for Islamic prayer?",
            draft_answer="Muslims must pray five times daily.",
            passages=sample_passages,
            agent_scores=sample_agent_scores,
            sanad_score=0.65,  # Below default threshold of 0.70
            metadata={"category": "worship"}
        )
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        mock_config = Mock()
        mock_config.thresholds.enhancement_threshold = 0.70
        mock_config.thresholds.max_retries = 2
        mock_config.thresholds.base_delay = 1.0
        mock_config.llm.openai.timeout = 3.0
        mock_config.llm.openai.max_tokens = 250
        mock_config.llm.primary_provider = "openai"
        mock_config.llm.openai.model = "gpt-3.5-turbo"
        
        # Mock domain configuration
        mock_domain = Mock()
        mock_domain.keywords = ["islam", "islamic", "prayer", "hajj", "quran", "charity"]
        mock_domain.enhancement_instructions = "6. For Islamic topics, prioritize authentic sources and scholarly consensus\n7. Use appropriate Islamic terminology and transliterations"
        mock_config.domain = mock_domain
        
        return mock_config
    
    @pytest.fixture
    def mock_baseline_llm(self):
        """Mock baseline LLM for testing."""
        mock_llm = AsyncMock()
        mock_response = Mock()
        mock_response.answer = "Muslims must perform five daily prayers (Salah) at specific times. According to Islamic sources, wudu (ablution) is required before prayer, and the prayer times are determined by the sun's position."
        mock_llm.draft.return_value = mock_response
        return mock_llm
    
    @patch('core.enhancer.get_config')
    @patch('core.enhancer.BaselineLLM')
    def test_enhancer_initialization(self, mock_llm_class, mock_get_config, mock_config):
        """Test that ResponseEnhancer initializes correctly."""
        mock_get_config.return_value = mock_config
        mock_llm_class.return_value = Mock()
        
        enhancer = ResponseEnhancer()
        
        assert enhancer.config == mock_config
        assert enhancer.enhancement_threshold == 0.70
        mock_get_config.assert_called_once()
        mock_llm_class.assert_called_once()
    
    @patch('core.enhancer.get_config')
    @patch('core.enhancer.BaselineLLM')
    async def test_enhancement_below_threshold(self, mock_llm_class, mock_get_config, 
                                             mock_config, mock_baseline_llm, enhancement_request):
        """Test enhancement when Sanad score is below threshold."""
        mock_get_config.return_value = mock_config
        mock_llm_class.return_value = mock_baseline_llm
        
        enhancer = ResponseEnhancer()
        response = await enhancer.enhance(enhancement_request)
        
        assert response.enhancement_applied is True
        assert response.enhanced_answer != enhancement_request.draft_answer
        assert "wudu" in response.enhanced_answer.lower()
        assert response.confidence > enhancement_request.sanad_score
        assert len(response.sources_used) > 0
        mock_baseline_llm.draft.assert_called_once()
    
    @patch('core.enhancer.get_config')
    @patch('core.enhancer.BaselineLLM')
    async def test_no_enhancement_above_threshold(self, mock_llm_class, mock_get_config,
                                                mock_config, mock_baseline_llm, enhancement_request):
        """Test no enhancement when Sanad score is above threshold."""
        mock_get_config.return_value = mock_config
        mock_llm_class.return_value = mock_baseline_llm
        
        # Set score above threshold
        enhancement_request.sanad_score = 0.75
        
        enhancer = ResponseEnhancer()
        response = await enhancer.enhance(enhancement_request)
        
        assert response.enhancement_applied is False
        assert response.enhanced_answer == enhancement_request.draft_answer
        assert response.enhancement_reason == "Score above threshold"
        assert response.confidence == enhancement_request.sanad_score
        mock_baseline_llm.draft.assert_not_called()
    
    @patch('core.enhancer.get_config')
    @patch('core.enhancer.BaselineLLM')
    async def test_enhancement_with_insufficient_passages(self, mock_llm_class, mock_get_config,
                                                        mock_config, mock_baseline_llm, enhancement_request):
        """Test enhancement behavior with insufficient passages."""
        mock_get_config.return_value = mock_config
        mock_llm_class.return_value = mock_baseline_llm
        
        # Set only one passage (insufficient)
        enhancement_request.passages = enhancement_request.passages[:1]
        
        enhancer = ResponseEnhancer()
        response = await enhancer.enhance(enhancement_request)
        
        assert response.enhancement_applied is False
        assert response.enhanced_answer == enhancement_request.draft_answer
        mock_baseline_llm.draft.assert_not_called()
    
    @patch('core.enhancer.get_config')
    @patch('core.enhancer.BaselineLLM')
    async def test_enhancement_llm_failure(self, mock_llm_class, mock_get_config,
                                         mock_config, enhancement_request):
        """Test enhancement fallback when LLM fails."""
        mock_get_config.return_value = mock_config
        mock_baseline_llm = AsyncMock()
        mock_baseline_llm.draft.side_effect = Exception("LLM API error")
        mock_llm_class.return_value = mock_baseline_llm
        
        enhancer = ResponseEnhancer()
        response = await enhancer.enhance(enhancement_request)
        
        assert response.enhancement_applied is False
        assert response.enhanced_answer == enhancement_request.draft_answer
        assert "Enhancement failed" in response.enhancement_reason
    
    @patch('core.enhancer.get_config')
    @patch('core.enhancer.BaselineLLM')
    async def test_enhancement_timeout(self, mock_llm_class, mock_get_config,
                                     mock_config, enhancement_request):
        """Test enhancement timeout handling."""
        mock_get_config.return_value = mock_config
        mock_baseline_llm = AsyncMock()
        mock_baseline_llm.draft.side_effect = asyncio.TimeoutError()
        mock_llm_class.return_value = mock_baseline_llm
        
        enhancer = ResponseEnhancer()
        response = await enhancer.enhance(enhancement_request)
        
        assert response.enhancement_applied is False
        assert response.enhanced_answer == enhancement_request.draft_answer
    
    @patch('core.enhancer.get_config')
    @patch('core.enhancer.BaselineLLM')
    def test_domain_query_detection(self, mock_llm_class, mock_get_config, mock_config):
        """Test domain-specific query detection logic."""
        # Mock domain configuration with Islamic keywords
        mock_domain = Mock()
        mock_domain.keywords = ["islam", "islamic", "prayer", "hajj", "quran", "charity"]
        mock_config.domain = mock_domain
        mock_get_config.return_value = mock_config
        mock_llm_class.return_value = Mock()
        
        enhancer = ResponseEnhancer()
        
        # Test domain-relevant queries
        assert enhancer._is_domain_relevant("What is the ruling on prayer?") is True
        assert enhancer._is_domain_relevant("Tell me about Hajj pilgrimage") is True
        assert enhancer._is_domain_relevant("What does the Quran say about charity?") is True
        
        # Test non-domain queries
        assert enhancer._is_domain_relevant("What is the weather today?") is False
        assert enhancer._is_domain_relevant("How do I cook pasta?") is False
        assert enhancer._is_domain_relevant("What is machine learning?") is False
        
        # Test with empty keywords (should return False)
        mock_domain.keywords = []
        assert enhancer._is_domain_relevant("What is the ruling on prayer?") is False
    
    @patch('core.enhancer.get_config')
    @patch('core.enhancer.BaselineLLM')
    def test_enhancement_prompt_building(self, mock_llm_class, mock_get_config,
                                       mock_config, enhancement_request):
        """Test enhancement prompt construction."""
        mock_get_config.return_value = mock_config
        mock_llm_class.return_value = Mock()
        
        enhancer = ResponseEnhancer()
        prompt = enhancer._build_enhancement_prompt(enhancement_request)
        
        assert enhancement_request.question in prompt
        assert enhancement_request.draft_answer in prompt
        assert "Passage 1" in prompt
        assert "precision" in prompt.lower()
        assert "provenance" in prompt.lower()
        assert "factual accuracy" in prompt
        assert "source citations" in prompt
    
    @patch('core.enhancer.get_config')
    @patch('core.enhancer.BaselineLLM')
    def test_should_enhance_logic(self, mock_llm_class, mock_get_config,
                                mock_config, enhancement_request):
        """Test the enhancement decision logic."""
        mock_get_config.return_value = mock_config
        mock_llm_class.return_value = Mock()
        
        enhancer = ResponseEnhancer()
        
        # Should enhance: low score with sufficient passages
        assert enhancer._should_enhance(enhancement_request) is True
        
        # Should not enhance: high score
        enhancement_request.sanad_score = 0.8
        assert enhancer._should_enhance(enhancement_request) is False
        
        # Should not enhance: insufficient passages
        enhancement_request.sanad_score = 0.6
        enhancement_request.passages = []
        assert enhancer._should_enhance(enhancement_request) is False
    
    @patch('core.enhancer.get_config')
    @patch('core.enhancer.BaselineLLM')
    def test_get_enhancement_stats(self, mock_llm_class, mock_get_config, mock_config):
        """Test enhancement statistics retrieval."""
        mock_get_config.return_value = mock_config
        mock_llm_class.return_value = Mock()
        
        enhancer = ResponseEnhancer()
        stats = enhancer.get_enhancement_stats()
        
        assert stats["enhancement_threshold"] == 0.70
        assert stats["llm_provider"] == "openai"
        assert stats["llm_model"] == "gpt-3.5-turbo"
        assert stats["max_tokens"] == 250
        assert stats["timeout_seconds"] == 3.0


class TestEnhancementIntegration:
    """Integration tests for enhancement with other components."""
    
    @patch('core.enhancer.get_config')
    @patch('core.enhancer.BaselineLLM')
    async def test_convenience_function(self, mock_llm_class, mock_get_config):
        """Test the convenience function for direct enhancement."""
        from core.enhancer import enhance_response
        
        mock_config = Mock()
        mock_config.thresholds.enhancement_threshold = 0.70
        mock_config.thresholds.max_retries = 2
        mock_config.thresholds.base_delay = 1.0
        mock_config.llm.openai.timeout = 3.0
        mock_config.llm.openai.max_tokens = 250
        mock_config.llm.primary_provider = "openai"
        mock_config.llm.openai.model = "gpt-3.5-turbo"
        
        # Mock domain configuration
        mock_domain = Mock()
        mock_domain.keywords = ["test", "sample"]
        mock_domain.enhancement_instructions = "Test enhancement instructions"
        mock_config.domain = mock_domain
        
        mock_get_config.return_value = mock_config
        
        mock_llm = AsyncMock()
        mock_response = Mock()
        mock_response.answer = "Enhanced answer with more details"
        mock_llm.draft.return_value = mock_response
        mock_llm_class.return_value = mock_llm
        
        passages = [
            Passage(
                text="Sample passage 1", 
                doc_id="doc1", 
                score=0.9, 
                metadata={},
                chunk_id="chunk_001",
                category="test",
                distance=0.1
            ),
            Passage(
                text="Sample passage 2", 
                doc_id="doc2", 
                score=0.8, 
                metadata={},
                chunk_id="chunk_002",
                category="test",
                distance=0.2
            )
        ]
        
        agent_scores = {
            "precision": AgentScore(
                score=0.6, explanation="Needs improvement", 
                confidence=0.8, agent_name="precision"
            )
        }
        
        response = await enhance_response(
            question="Test question",
            draft_answer="Basic answer",
            passages=passages,
            agent_scores=agent_scores,
            sanad_score=0.65
        )
        
        assert isinstance(response, EnhancementResponse)
        assert response.enhancement_applied is True
        assert response.enhanced_answer == "Enhanced answer with more details"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
