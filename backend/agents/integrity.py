"""
IntegrityAgent for Sanad v2.
Validates source authority and reliability of retrieved passages.
"""

import asyncio
from typing import Any, Dict, List

from loguru import logger

try:
    from ..core.baseline_llm import BaselineLLM
    from ..core.config import get_config
    from .base import AgentInput, AgentScore, BaseAgent
except ImportError:
    from base import AgentInput, AgentScore, BaseAgent

    from core.baseline_llm import BaselineLLM
    from core.config import get_config


class IntegrityAgent(BaseAgent):
    """
    Agent that evaluates the integrity and authority of source documents.
    Assesses whether the retrieved passages come from authoritative, reliable sources.
    """

    def __init__(self):
        """Initialize the IntegrityAgent."""
        super().__init__("IntegrityAgent")
        self.config = get_config()
        self.llm = BaselineLLM()

        # Source authority mapping
        self.source_authority = {
            "labour_law": 0.95,  # Official Qatar Labour Law
            "QNDS3_EN": 0.90,  # Official National Development Strategy
            "ministry": 0.90,  # Ministry documents
            "government": 0.85,  # Other government sources
            "research_report": 0.70,  # Research reports (peer-reviewed)
            "academic": 0.65,  # Academic sources
            "news": 0.40,  # News sources
            "blog": 0.20,  # Blog posts
            "unknown": 0.30,  # Unknown sources
        }

        logger.info("Initialized IntegrityAgent with source authority mapping")

    async def evaluate(self, input_data: AgentInput) -> AgentScore:
        """
        Evaluate the integrity of sources used in the draft answer.

        Args:
            input_data: Input containing question, draft answer, and passages

        Returns:
            AgentScore with integrity assessment
        """
        try:
            # Step 1: Assess source authority
            authority_score = self._assess_source_authority(input_data.passages)

            # Step 2: Check for contradictions
            contradiction_score = await self._check_contradictions(input_data)

            # Step 3: Evaluate source consistency
            consistency_score = self._evaluate_source_consistency(input_data.passages)

            # Step 4: Compute composite integrity score
            composite_score = (
                authority_score * 0.5  # 50% source authority
                + contradiction_score * 0.3  # 30% contradiction check
                + consistency_score * 0.2  # 20% consistency
            )

            # Step 5: Generate explanation
            explanation = self._generate_explanation(
                authority_score,
                contradiction_score,
                consistency_score,
                input_data.passages,
            )

            logger.debug(
                f"IntegrityAgent: authority={authority_score:.3f}, "
                f"contradiction={contradiction_score:.3f}, "
                f"consistency={consistency_score:.3f}, "
                f"composite={composite_score:.3f}"
            )

            return AgentScore(
                score=composite_score,
                explanation=explanation,
                confidence=0.85,  # High confidence in integrity assessment
                agent_name=self.name,
            )

        except Exception as e:
            logger.error(f"IntegrityAgent evaluation failed: {str(e)}")
            return AgentScore(
                score=0.5,
                explanation=f"Integrity evaluation failed: {str(e)}",
                confidence=0.0,
                agent_name=self.name,
            )

    def _assess_source_authority(self, passages: List[Any]) -> float:
        """
        Assess the authority of source documents.

        Args:
            passages: List of retrieved passages

        Returns:
            Authority score (0.0 to 1.0)
        """
        if not passages:
            return 0.3

        total_authority = 0.0
        for passage in passages:
            doc_id = getattr(passage, "doc_id", "").lower()

            # Determine source authority
            authority = self.source_authority.get("unknown", 0.30)

            # Check against known source patterns
            for source_type, score in self.source_authority.items():
                if source_type in doc_id:
                    authority = score
                    break

            total_authority += authority

        average_authority = total_authority / len(passages)
        logger.debug(
            f"Source authority assessment: {average_authority:.3f} from {len(passages)} passages"
        )

        return min(max(average_authority, 0.0), 1.0)

    async def _check_contradictions(self, input_data: AgentInput) -> float:
        """
        Check for contradictions between passages and draft answer.

        Args:
            input_data: Input data including question, answer, and passages

        Returns:
            Contradiction score (1.0 = no contradictions, 0.0 = major contradictions)
        """
        try:
            # Build prompt for contradiction detection
            prompt = self._build_contradiction_prompt(
                input_data.question, input_data.draft_answer, input_data.passages
            )

            # Call LLM to assess contradictions
            response = await self.llm.draft(prompt)
            contradiction_assessment = response.answer.lower()

            # Parse LLM response for contradiction indicators
            if (
                "no contradictions" in contradiction_assessment
                or "consistent" in contradiction_assessment
            ):
                return 1.0
            elif (
                "minor inconsistency" in contradiction_assessment
                or "slight variation" in contradiction_assessment
            ):
                return 0.8
            elif (
                "contradiction" in contradiction_assessment
                or "inconsistent" in contradiction_assessment
            ):
                return 0.3
            else:
                return 0.7  # Default when unclear

        except Exception as e:
            logger.warning(f"Contradiction check failed: {str(e)}")
            return 0.7  # Default neutral score

    def _evaluate_source_consistency(self, passages: List[Any]) -> float:
        """
        Evaluate consistency across multiple sources.

        Args:
            passages: List of retrieved passages

        Returns:
            Consistency score (0.0 to 1.0)
        """
        if len(passages) <= 1:
            return 0.8  # Single source - no consistency issues

        # Group passages by source
        sources = {}
        for passage in passages:
            doc_id = getattr(passage, "doc_id", "unknown")
            if doc_id not in sources:
                sources[doc_id] = []
            sources[doc_id].append(passage)

        # More diverse sources generally indicate better consistency
        num_sources = len(sources)

        if num_sources >= 3:
            return 0.9  # Multiple independent sources
        elif num_sources == 2:
            return 0.8  # Two sources
        else:
            return 0.7  # Single source repeated

    def _build_contradiction_prompt(
        self, question: str, answer: str, passages: List[Any]
    ) -> str:
        """
        Build prompt for LLM-based contradiction detection.

        Args:
            question: Original question
            answer: Draft answer
            passages: Retrieved passages

        Returns:
            Prompt string for contradiction detection
        """
        passages_text = "\n\n".join(
            [
                f"Source {i+1}: {getattr(p, 'text', str(p))[:200]}..."
                for i, p in enumerate(passages[:3])  # Use top 3 passages
            ]
        )

        prompt = f"""Analyze if there are any contradictions between the answer and the provided sources.

QUESTION: {question}

ANSWER: {answer}

SOURCES:
{passages_text}

Task: Check for contradictions, inconsistencies, or factual errors between the answer and sources.

Respond with one of:
- "No contradictions - answer is consistent with sources"
- "Minor inconsistency - small variations in details"
- "Major contradiction - answer conflicts with sources"

Assessment:"""

        return prompt

    def _generate_explanation(
        self,
        authority_score: float,
        contradiction_score: float,
        consistency_score: float,
        passages: List[Any],
    ) -> str:
        """
        Generate human-readable explanation of integrity assessment.

        Args:
            authority_score: Source authority score
            contradiction_score: Contradiction assessment score
            consistency_score: Source consistency score
            passages: Retrieved passages

        Returns:
            Explanation string
        """
        explanations = []

        # Source authority explanation
        if authority_score >= 0.8:
            explanations.append(
                "High-authority sources (government/official documents)"
            )
        elif authority_score >= 0.6:
            explanations.append("Moderate-authority sources (research/academic)")
        else:
            explanations.append("Lower-authority sources")

        # Contradiction explanation
        if contradiction_score >= 0.8:
            explanations.append("no contradictions detected")
        elif contradiction_score >= 0.6:
            explanations.append("minor inconsistencies found")
        else:
            explanations.append("potential contradictions identified")

        # Consistency explanation
        source_count = len(set(getattr(p, "doc_id", "unknown") for p in passages))
        explanations.append(f"verified across {source_count} source(s)")

        return f"Source integrity: {', '.join(explanations)}"
