#!/usr/bin/env python3
"""
Simple integration test for the ResponseEnhancer module.
Tests the enhancer functionality without complex imports.
"""

import sys
import os
import asyncio
from unittest.mock import Mock, AsyncMock

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Test imports
try:
    from core.enhancer import ResponseEnhancer, EnhancementRequest, EnhancementResponse
    from agents.base import AgentScore, Passage
    print("✓ All imports successful")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)


async def test_enhancer_basic_functionality():
    """Test basic enhancer functionality with mocked dependencies."""
    print("\n=== Testing ResponseEnhancer Basic Functionality ===")
    
    # Mock configuration
    mock_config = Mock()
    mock_config.thresholds.enhancement_threshold = 0.70
    mock_config.llm.openai.timeout = 3.0
    mock_config.llm.openai.max_tokens = 250
    mock_config.llm.primary_provider = "openai"
    mock_config.llm.openai.model = "gpt-3.5-turbo"
    
    # Mock baseline LLM
    mock_llm = AsyncMock()
    mock_response = Mock()
    mock_response.answer = "Enhanced answer with detailed Islamic prayer requirements including Fajr, Dhuhr, Asr, Maghrib, and Isha prayers."
    mock_llm.draft.return_value = mock_response
    
    # Patch the dependencies
    import core.enhancer
    original_get_config = getattr(core.enhancer, 'get_config', None)
    original_baseline_llm = getattr(core.enhancer, 'BaselineLLM', None)
    
    core.enhancer.get_config = lambda: mock_config
    core.enhancer.BaselineLLM = lambda: mock_llm
    
    try:
        # Create enhancer instance
        enhancer = ResponseEnhancer()
        print("✓ ResponseEnhancer initialized successfully")
        
        # Create test data
        passages = [
            Passage(
                doc_id="hadith_001",
                chunk_id="chunk_001",
                text="The five daily prayers are Fajr, Dhuhr, Asr, Maghrib, and Isha.",
                category="hadith",
                score=0.9,
                distance=0.1
            ),
            Passage(
                doc_id="quran_002",
                chunk_id="chunk_002",
                text="Prayer is the second pillar of Islam.",
                category="quran",
                score=0.85,
                distance=0.15
            )
        ]
        
        agent_scores = {
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
            )
        }
        
        # Create enhancement request
        request = EnhancementRequest(
            question="What are the requirements for Islamic prayer?",
            draft_answer="Muslims must pray five times daily.",
            passages=passages,
            agent_scores=agent_scores,
            sanad_score=0.65,  # Below threshold
            metadata={"category": "worship"}
        )
        
        print("✓ Enhancement request created successfully")
        
        # Test enhancement
        response = await enhancer.enhance(request)
        
        print("✓ Enhancement completed successfully")
        print(f"  - Enhancement applied: {response.enhancement_applied}")
        print(f"  - Original answer: {request.draft_answer}")
        print(f"  - Enhanced answer: {response.enhanced_answer}")
        print(f"  - Confidence boost: {response.confidence:.3f} (from {request.sanad_score:.3f})")
        print(f"  - Sources used: {len(response.sources_used)}")
        
        # Verify enhancement was applied
        assert response.enhancement_applied is True
        assert response.enhanced_answer != request.draft_answer
        assert response.confidence > request.sanad_score
        assert len(response.sources_used) > 0
        
        print("✓ All enhancement assertions passed")
        
        # Test high score (no enhancement)
        request.sanad_score = 0.80  # Above threshold
        response_high = await enhancer.enhance(request)
        
        assert response_high.enhancement_applied is False
        assert response_high.enhanced_answer == request.draft_answer
        print("✓ High score test passed (no enhancement applied)")
        
        # Test enhancement statistics
        stats = enhancer.get_enhancement_stats()
        print(f"✓ Enhancement stats: {stats}")
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Restore original functions
        if original_get_config:
            core.enhancer.get_config = original_get_config
        if original_baseline_llm:
            core.enhancer.BaselineLLM = original_baseline_llm


async def test_enhancement_decision_logic():
    """Test the enhancement decision logic."""
    print("\n=== Testing Enhancement Decision Logic ===")
    
    # Mock minimal config
    mock_config = Mock()
    mock_config.thresholds.enhancement_threshold = 0.70
    mock_config.llm.openai.timeout = 3.0
    mock_config.llm.openai.max_tokens = 250
    mock_config.llm.primary_provider = "openai"
    mock_config.llm.openai.model = "gpt-3.5-turbo"
    
    import core.enhancer
    core.enhancer.get_config = lambda: mock_config
    core.enhancer.BaselineLLM = lambda: Mock()
    
    try:
        enhancer = ResponseEnhancer()
        
        # Create sample passages for testing
        sample_passages = [
            Passage(
                doc_id="test_001",
                chunk_id="chunk_001",
                text="Test passage 1",
                category="test",
                score=0.8,
                distance=0.2
            ),
            Passage(
                doc_id="test_002",
                chunk_id="chunk_002",
                text="Test passage 2",
                category="test",
                score=0.7,
                distance=0.3
            )
        ]
        
        # Test cases
        test_cases = [
            {
                "name": "Low score with passages",
                "sanad_score": 0.6,
                "passages": sample_passages,
                "expected": True
            },
            {
                "name": "High score",
                "sanad_score": 0.8,
                "passages": sample_passages,
                "expected": False
            },
            {
                "name": "Low score without passages",
                "sanad_score": 0.6,
                "passages": [],
                "expected": False
            },
            {
                "name": "Threshold score",
                "sanad_score": 0.70,
                "passages": sample_passages,
                "expected": False
            }
        ]
        
        for case in test_cases:
            request = EnhancementRequest(
                question="Test question",
                draft_answer="Test answer",
                passages=case["passages"],
                agent_scores={},
                sanad_score=case["sanad_score"],
                metadata={}
            )
            
            result = enhancer._should_enhance(request)
            assert result == case["expected"], f"Failed case: {case['name']}"
            print(f"✓ {case['name']}: {result} (expected {case['expected']})")
        
        return True
        
    except Exception as e:
        print(f"✗ Decision logic test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("=== Sanad v2 ResponseEnhancer Integration Test ===")
    
    tests = [
        test_enhancer_basic_functionality,
        test_enhancement_decision_logic
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if await test():
                passed += 1
                print(f"✓ {test.__name__} PASSED")
            else:
                print(f"✗ {test.__name__} FAILED")
        except Exception as e:
            print(f"✗ {test.__name__} ERROR: {e}")
    
    print(f"\n=== Test Results: {passed}/{total} tests passed ===")
    
    if passed == total:
        print("🎉 All tests passed! ResponseEnhancer integration is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
