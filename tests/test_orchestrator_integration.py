"""
Integration tests for the orchestrator with the new ResponseEnhancer.
Tests the complete verification flow including enhancement.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, List

# Import the modules to test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from coordinator.orchestrator import SanadCoordinator, CoordinatorInput, VerificationResponse
from agents.base import BaseAgent, AgentInput, AgentScore, Passage


class MockAgent(BaseAgent):
    """Mock agent for testing."""
    
    def __init__(self, name: str, score: float, explanation: str = "Mock evaluation"):
        self.name = name
        self._score = score
        self._explanation = explanation
    
    async def evaluate(self, input_data: AgentInput) -> AgentScore:
        """Mock evaluation that returns predefined score."""
        return AgentScore(
            score=self._score,
            explanation=self._explanation,
            confidence=0.8,
            agent_name=self.name.lower()
        )


class TestOrchestratorEnhancerIntegration:
    """Test suite for orchestrator-enhancer integration."""
    
    @pytest.fixture
    def sample_passages(self) -> List[Passage]:
        """Create sample passages for testing."""
        return [
            Passage(
                text="The five daily prayers are Fajr, Dhuhr, Asr, Maghrib, and Isha.",
                doc_id="hadith_001",
                score=0.9,
                metadata={"source": "Sahih Bukhari"}
            ),
            Passage(
                text="Prayer is the second pillar of Islam after Shahada.",
                doc_id="quran_002",
                score=0.85,
                metadata={"source": "Quran"}
            )
        ]
    
    @pytest.fixture
    def coordinator_input(self, sample_passages) -> CoordinatorInput:
        """Create coordinator input for testing."""
        return CoordinatorInput(
            question="What are the five daily prayers in Islam?",
            draft_answer="Muslims pray five times a day.",
            passages=sample_passages,
            metadata={"category": "worship"}
        )
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        mock_config = Mock()
        
        # Agent weights
        mock_config.agent_weights.integrity = 0.4
        mock_config.agent_weights.precision = 0.3
        mock_config.agent_weights.provenance = 0.2
        mock_config.agent_weights.domain = 0.1
        
        # Thresholds
        mock_config.thresholds.enhancement_threshold = 0.70
        
        # LLM config
        mock_config.llm.openai.timeout = 3.0
        mock_config.llm.openai.max_tokens = 250
        mock_config.llm.primary_provider = "openai"
        mock_config.llm.openai.model = "gpt-3.5-turbo"
        
        return mock_config
    
    @pytest.fixture
    def mock_baseline_llm(self):
        """Mock baseline LLM for testing."""
        mock_llm = AsyncMock()
        mock_response = Mock()
        mock_response.answer = "The five daily prayers in Islam are Fajr (dawn), Dhuhr (midday), Asr (afternoon), Maghrib (sunset), and Isha (night). According to Islamic sources, prayer is the second pillar of Islam."
        mock_llm.draft.return_value = mock_response
        return mock_llm
    
    @patch('coordinator.orchestrator.get_config')
    @patch('coordinator.orchestrator.BaselineLLM')
    @patch('core.enhancer.get_config')
    @patch('core.enhancer.BaselineLLM')
    async def test_orchestrator_with_enhancement_needed(self, enhancer_llm_class, enhancer_config,
                                                       orch_llm_class, orch_config,
                                                       mock_config, mock_baseline_llm,
                                                       coordinator_input):
        """Test orchestrator flow when enhancement is needed (low Sanad score)."""
        # Setup mocks
        orch_config.return_value = mock_config
        enhancer_config.return_value = mock_config
        orch_llm_class.return_value = mock_baseline_llm
        enhancer_llm_class.return_value = mock_baseline_llm
        
        # Create coordinator
        coordinator = SanadCoordinator()
        
        # Register agents with low scores to trigger enhancement
        coordinator.register_agent(MockAgent("PrecisionAgent", 0.5, "Answer lacks detail"))
        coordinator.register_agent(MockAgent("ProvenanceAgent", 0.4, "Missing citations"))
        coordinator.register_agent(MockAgent("DomainAgent", 0.6, "Good terminology"))
        coordinator.register_agent(MockAgent("IntegrityAgent", 0.7, "Logically sound"))
        
        # Execute verification
        response = await coordinator.verify(coordinator_input)
        
        # Verify response
        assert isinstance(response, VerificationResponse)
        assert response.sanad_score < 0.70  # Should be below threshold
        assert response.answer != coordinator_input.draft_answer  # Should be enhanced
        assert "Fajr" in response.answer  # Should contain enhanced content
        assert response.processing_time_ms > 0
        
        # Verify LLM was called for enhancement
        mock_baseline_llm.draft.assert_called_once()
    
    @patch('coordinator.orchestrator.get_config')
    @patch('coordinator.orchestrator.BaselineLLM')
    @patch('core.enhancer.get_config')
    @patch('core.enhancer.BaselineLLM')
    async def test_orchestrator_without_enhancement(self, enhancer_llm_class, enhancer_config,
                                                   orch_llm_class, orch_config,
                                                   mock_config, mock_baseline_llm,
                                                   coordinator_input):
        """Test orchestrator flow when enhancement is not needed (high Sanad score)."""
        # Setup mocks
        orch_config.return_value = mock_config
        enhancer_config.return_value = mock_config
        orch_llm_class.return_value = mock_baseline_llm
        enhancer_llm_class.return_value = mock_baseline_llm
        
        # Create coordinator
        coordinator = SanadCoordinator()
        
        # Register agents with high scores to avoid enhancement
        coordinator.register_agent(MockAgent("PrecisionAgent", 0.8, "Accurate answer"))
        coordinator.register_agent(MockAgent("ProvenanceAgent", 0.9, "Good citations"))
        coordinator.register_agent(MockAgent("DomainAgent", 0.7, "Proper terminology"))
        coordinator.register_agent(MockAgent("IntegrityAgent", 0.8, "Consistent"))
        
        # Execute verification
        response = await coordinator.verify(coordinator_input)
        
        # Verify response
        assert isinstance(response, VerificationResponse)
        assert response.sanad_score >= 0.70  # Should be above threshold
        assert response.answer == coordinator_input.draft_answer  # Should not be enhanced
        assert response.processing_time_ms > 0
        
        # Verify LLM was not called for enhancement
        mock_baseline_llm.draft.assert_not_called()
    
    @patch('coordinator.orchestrator.get_config')
    @patch('coordinator.orchestrator.BaselineLLM')
    @patch('core.enhancer.get_config')
    @patch('core.enhancer.BaselineLLM')
    async def test_orchestrator_enhancement_failure_fallback(self, enhancer_llm_class, enhancer_config,
                                                            orch_llm_class, orch_config,
                                                            mock_config, coordinator_input):
        """Test orchestrator fallback when enhancement fails."""
        # Setup mocks
        orch_config.return_value = mock_config
        enhancer_config.return_value = mock_config
        
        # Mock LLM that fails during enhancement
        failing_llm = AsyncMock()
        failing_llm.draft.side_effect = Exception("LLM API error")
        orch_llm_class.return_value = failing_llm
        enhancer_llm_class.return_value = failing_llm
        
        # Create coordinator
        coordinator = SanadCoordinator()
        
        # Register agents with low scores to trigger enhancement
        coordinator.register_agent(MockAgent("PrecisionAgent", 0.5, "Needs improvement"))
        coordinator.register_agent(MockAgent("ProvenanceAgent", 0.4, "Missing sources"))
        
        # Execute verification
        response = await coordinator.verify(coordinator_input)
        
        # Verify graceful fallback
        assert isinstance(response, VerificationResponse)
        assert response.answer == coordinator_input.draft_answer  # Should fallback to original
        assert response.processing_time_ms > 0
    
    @patch('coordinator.orchestrator.get_config')
    @patch('coordinator.orchestrator.BaselineLLM')
    @patch('core.enhancer.get_config')
    @patch('core.enhancer.BaselineLLM')
    async def test_orchestrator_with_no_agents(self, enhancer_llm_class, enhancer_config,
                                              orch_llm_class, orch_config,
                                              mock_config, mock_baseline_llm,
                                              coordinator_input):
        """Test orchestrator behavior with no registered agents."""
        # Setup mocks
        orch_config.return_value = mock_config
        enhancer_config.return_value = mock_config
        orch_llm_class.return_value = mock_baseline_llm
        enhancer_llm_class.return_value = mock_baseline_llm
        
        # Create coordinator without registering agents
        coordinator = SanadCoordinator()
        
        # Execute verification
        response = await coordinator.verify(coordinator_input)
        
        # Verify response with default low score
        assert isinstance(response, VerificationResponse)
        assert response.sanad_score == 0.3  # Default low score
        assert response.answer != coordinator_input.draft_answer  # Should be enhanced due to low score
        assert response.processing_time_ms > 0
    
    @patch('coordinator.orchestrator.get_config')
    @patch('coordinator.orchestrator.BaselineLLM')
    @patch('core.enhancer.get_config')
    @patch('core.enhancer.BaselineLLM')
    def test_orchestrator_agent_registration(self, enhancer_llm_class, enhancer_config,
                                           orch_llm_class, orch_config,
                                           mock_config, mock_baseline_llm):
        """Test agent registration in orchestrator."""
        # Setup mocks
        orch_config.return_value = mock_config
        enhancer_config.return_value = mock_config
        orch_llm_class.return_value = mock_baseline_llm
        enhancer_llm_class.return_value = mock_baseline_llm
        
        # Create coordinator
        coordinator = SanadCoordinator()
        
        # Register agents
        precision_agent = MockAgent("PrecisionAgent", 0.8)
        provenance_agent = MockAgent("ProvenanceAgent", 0.7)
        
        coordinator.register_agent(precision_agent)
        coordinator.register_agent(provenance_agent)
        
        # Verify registration
        assert "precision" in coordinator.agents
        assert "provenance" in coordinator.agents
        assert coordinator.agents["precision"] == precision_agent
        assert coordinator.agents["provenance"] == provenance_agent
    
    @patch('coordinator.orchestrator.get_config')
    @patch('coordinator.orchestrator.BaselineLLM')
    @patch('core.enhancer.get_config')
    @patch('core.enhancer.BaselineLLM')
    async def test_orchestrator_agent_timeout_handling(self, enhancer_llm_class, enhancer_config,
                                                      orch_llm_class, orch_config,
                                                      mock_config, mock_baseline_llm,
                                                      coordinator_input):
        """Test orchestrator handling of agent timeouts."""
        # Setup mocks
        orch_config.return_value = mock_config
        enhancer_config.return_value = mock_config
        orch_llm_class.return_value = mock_baseline_llm
        enhancer_llm_class.return_value = mock_baseline_llm
        
        # Create coordinator
        coordinator = SanadCoordinator()
        
        # Create agent that times out
        class TimeoutAgent(BaseAgent):
            def __init__(self):
                self.name = "TimeoutAgent"
            
            async def evaluate(self, input_data: AgentInput) -> AgentScore:
                await asyncio.sleep(2)  # Longer than 850ms timeout
                return AgentScore(score=0.8, explanation="", confidence=0.8, agent_name="timeout")
        
        coordinator.register_agent(TimeoutAgent())
        coordinator.register_agent(MockAgent("PrecisionAgent", 0.7, "Good answer"))
        
        # Execute verification
        response = await coordinator.verify(coordinator_input)
        
        # Verify response (should handle timeout gracefully)
        assert isinstance(response, VerificationResponse)
        assert response.processing_time_ms > 0
        # Should still work with remaining agents


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
