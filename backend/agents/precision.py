"""
PrecisionAgent for Sanad v2.
Checks claim-passage consistency and factual accuracy of the draft answer.
"""

import asyncio
import re
from typing import Any, Dict, List, Tuple

from loguru import logger

try:
    from ..core.baseline_llm import BaselineLLM
    from ..core.config import get_config
    from .base import AgentInput, AgentScore, BaseAgent
except ImportError:
    from base import AgentInput, AgentScore, BaseAgent

    from core.baseline_llm import BaselineLLM
    from core.config import get_config


class PrecisionAgent(BaseAgent):
    """
    Agent that evaluates the precision and factual accuracy of the draft answer.
    Checks whether claims in the answer are supported by the retrieved passages.
    """

    def __init__(self):
        """Initialize the PrecisionAgent."""
        super().__init__("PrecisionAgent")
        self.config = get_config()
        self.llm = BaselineLLM()

        # Precision evaluation weights
        self.weights = {
            "factual_accuracy": 0.4,  # 40% - Are facts correct?
            "claim_support": 0.3,  # 30% - Are claims backed by passages?
            "specificity": 0.2,  # 20% - Is answer specific and detailed?
            "relevance": 0.1,  # 10% - Does answer address the question?
        }

        logger.info("Initialized PrecisionAgent with factual accuracy focus")

    async def evaluate(self, input_data: AgentInput) -> AgentScore:
        """
        Evaluate the precision of the draft answer against retrieved passages.

        Args:
            input_data: Input containing question, draft answer, and passages

        Returns:
            AgentScore with precision assessment
        """
        try:
            # Step 1: Check factual accuracy
            factual_score = await self._check_factual_accuracy(input_data)

            # Step 2: Evaluate claim support
            claim_support_score = await self._evaluate_claim_support(input_data)

            # Step 3: Assess answer specificity
            specificity_score = self._assess_specificity(input_data.draft_answer)

            # Step 4: Check relevance to question
            relevance_score = await self._check_relevance(input_data)

            # Step 5: Compute composite precision score
            composite_score = (
                factual_score * self.weights["factual_accuracy"]
                + claim_support_score * self.weights["claim_support"]
                + specificity_score * self.weights["specificity"]
                + relevance_score * self.weights["relevance"]
            )

            # Step 6: Generate explanation
            explanation = self._generate_explanation(
                factual_score, claim_support_score, specificity_score, relevance_score
            )

            logger.debug(
                f"PrecisionAgent: factual={factual_score:.3f}, "
                f"claim_support={claim_support_score:.3f}, "
                f"specificity={specificity_score:.3f}, "
                f"relevance={relevance_score:.3f}, "
                f"composite={composite_score:.3f}"
            )

            return AgentScore(
                score=composite_score,
                explanation=explanation,
                confidence=0.80,  # Good confidence in precision assessment
                agent_name=self.name,
            )

        except Exception as e:
            logger.error(f"PrecisionAgent evaluation failed: {str(e)}")
            return AgentScore(
                score=0.5,
                explanation=f"Precision evaluation failed: {str(e)}",
                confidence=0.0,
                agent_name=self.name,
            )

    async def _check_factual_accuracy(self, input_data: AgentInput) -> float:
        """
        Check factual accuracy of the draft answer against passages.

        Args:
            input_data: Input data including question, answer, and passages

        Returns:
            Factual accuracy score (0.0 to 1.0)
        """
        try:
            # Build prompt for factual verification
            prompt = self._build_factual_verification_prompt(
                input_data.question, input_data.draft_answer, input_data.passages
            )

            # Call LLM to verify facts
            response = await self.llm.draft(prompt)
            assessment = response.answer.lower()

            # Parse LLM response for accuracy indicators
            if "highly accurate" in assessment or "fully supported" in assessment:
                return 0.95
            elif "mostly accurate" in assessment or "largely supported" in assessment:
                return 0.80
            elif "partially accurate" in assessment or "some support" in assessment:
                return 0.60
            elif "minor inaccuracies" in assessment:
                return 0.70
            elif "inaccurate" in assessment or "not supported" in assessment:
                return 0.30
            else:
                return 0.65  # Default when unclear

        except Exception as e:
            logger.warning(f"Factual accuracy check failed: {str(e)}")
            return 0.65  # Default neutral score

    async def _evaluate_claim_support(self, input_data: AgentInput) -> float:
        """
        Evaluate how well claims in the answer are supported by passages.

        Args:
            input_data: Input data including answer and passages

        Returns:
            Claim support score (0.0 to 1.0)
        """
        try:
            # Extract key claims from the answer
            claims = self._extract_claims(input_data.draft_answer)

            if not claims:
                return 0.7  # No specific claims to verify

            # Check each claim against passages
            supported_claims = 0
            total_claims = len(claims)

            for claim in claims:
                if await self._is_claim_supported(claim, input_data.passages):
                    supported_claims += 1

            support_ratio = supported_claims / total_claims if total_claims > 0 else 0.7

            logger.debug(
                f"Claim support: {supported_claims}/{total_claims} claims supported"
            )
            return min(max(support_ratio, 0.0), 1.0)

        except Exception as e:
            logger.warning(f"Claim support evaluation failed: {str(e)}")
            return 0.65

    def _assess_specificity(self, answer: str) -> float:
        """
        Assess the specificity and detail level of the answer.

        Args:
            answer: Draft answer text

        Returns:
            Specificity score (0.0 to 1.0)
        """
        specificity_indicators = {
            # Numbers and specific values
            "numbers": len(re.findall(r"\b\d+(?:\.\d+)?\b", answer)) * 0.1,
            # Specific terms (dates, percentages, names)
            "dates": len(re.findall(r"\b\d{4}\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b", answer))
            * 0.15,
            "percentages": len(re.findall(r"\b\d+(?:\.\d+)?%\b", answer)) * 0.2,
            "proper_nouns": len(
                re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", answer)
            )
            * 0.05,
            # Specific language vs vague language
            "specific_terms": sum(
                0.1
                for term in ["exactly", "specifically", "precisely", "according to"]
                if term in answer.lower()
            ),
            "vague_penalty": sum(
                -0.1
                for term in [
                    "generally",
                    "usually",
                    "often",
                    "sometimes",
                    "might",
                    "may",
                ]
                if term in answer.lower()
            ),
        }

        # Calculate base specificity score
        base_score = sum(specificity_indicators.values())

        # Normalize and apply length bonus for detailed answers
        length_bonus = min(
            len(answer.split()) / 100, 0.2
        )  # Up to 0.2 bonus for longer answers

        final_score = base_score + length_bonus + 0.5  # Base score of 0.5

        return min(max(final_score, 0.0), 1.0)

    async def _check_relevance(self, input_data: AgentInput) -> float:
        """
        Check if the answer directly addresses the question asked.

        Args:
            input_data: Input data including question and answer

        Returns:
            Relevance score (0.0 to 1.0)
        """
        try:
            # Build prompt for relevance check
            prompt = f"""Evaluate how well this answer addresses the specific question asked.

QUESTION: {input_data.question}

ANSWER: {input_data.draft_answer}

Task: Rate how directly and completely the answer addresses the question.

Respond with one of:
- "Directly addresses - complete answer to the question"
- "Mostly relevant - addresses main aspects of the question"
- "Partially relevant - touches on some aspects"
- "Tangentially relevant - related but doesn't answer the question"
- "Irrelevant - does not address the question"

Relevance assessment:"""

            response = await self.llm.draft(prompt)
            assessment = response.answer.lower()

            if "directly addresses" in assessment:
                return 0.95
            elif "mostly relevant" in assessment:
                return 0.80
            elif "partially relevant" in assessment:
                return 0.60
            elif "tangentially relevant" in assessment:
                return 0.40
            elif "irrelevant" in assessment:
                return 0.20
            else:
                return 0.70  # Default when unclear

        except Exception as e:
            logger.warning(f"Relevance check failed: {str(e)}")
            return 0.70

    def _extract_claims(self, answer: str) -> List[str]:
        """
        Extract key factual claims from the answer.

        Args:
            answer: Answer text

        Returns:
            List of extracted claims
        """
        # Split into sentences
        sentences = re.split(r"[.!?]+", answer)

        # Filter for sentences that contain factual claims
        claims = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10:  # Ignore very short sentences
                # Look for factual indicators
                if any(
                    indicator in sentence.lower()
                    for indicator in [
                        "is",
                        "are",
                        "must",
                        "shall",
                        "should",
                        "according to",
                        "requires",
                        "allows",
                        "prohibits",
                        "states",
                        "specifies",
                    ]
                ):
                    claims.append(sentence)

        return claims[:5]  # Limit to top 5 claims for efficiency

    async def _is_claim_supported(self, claim: str, passages: List[Any]) -> bool:
        """
        Check if a specific claim is supported by the passages.

        Args:
            claim: Claim to verify
            passages: List of passages to check against

        Returns:
            True if claim is supported, False otherwise
        """
        try:
            # Build passages context
            passages_text = "\n\n".join(
                [
                    f"Passage {i+1}: {getattr(p, 'text', str(p))[:300]}..."
                    for i, p in enumerate(passages[:3])
                ]
            )

            prompt = f"""Check if the following claim is supported by the provided passages.

CLAIM: {claim}

PASSAGES:
{passages_text}

Task: Determine if the claim is supported, contradicted, or not mentioned in the passages.

Respond with only:
- "SUPPORTED" if the claim is backed by the passages
- "NOT_SUPPORTED" if the claim is not backed or contradicted

Assessment:"""

            response = await self.llm.draft(prompt)
            assessment = response.answer.upper()

            return "SUPPORTED" in assessment

        except Exception as e:
            logger.warning(f"Claim support check failed for claim: {claim[:50]}...")
            return False

    def _build_factual_verification_prompt(
        self, question: str, answer: str, passages: List[Any]
    ) -> str:
        """
        Build prompt for factual verification.

        Args:
            question: Original question
            answer: Draft answer
            passages: Retrieved passages

        Returns:
            Verification prompt string
        """
        passages_text = "\n\n".join(
            [
                f"Source {i+1}: {getattr(p, 'text', str(p))[:400]}..."
                for i, p in enumerate(passages[:4])  # Use top 4 passages
            ]
        )

        prompt = f"""Verify the factual accuracy of this answer against the provided sources.

QUESTION: {question}

ANSWER: {answer}

SOURCES:
{passages_text}

Task: Check if the facts, numbers, and claims in the answer are accurate according to the sources.

Respond with one of:
- "Highly accurate - all facts supported by sources"
- "Mostly accurate - minor discrepancies only"
- "Partially accurate - some facts supported"
- "Largely inaccurate - major factual errors"

Accuracy assessment:"""

        return prompt

    def _generate_explanation(
        self,
        factual_score: float,
        claim_support_score: float,
        specificity_score: float,
        relevance_score: float,
    ) -> str:
        """
        Generate human-readable explanation of precision assessment.

        Args:
            factual_score: Factual accuracy score
            claim_support_score: Claim support score
            specificity_score: Specificity score
            relevance_score: Relevance score

        Returns:
            Explanation string
        """
        explanations = []

        # Factual accuracy explanation
        if factual_score >= 0.8:
            explanations.append("factually accurate")
        elif factual_score >= 0.6:
            explanations.append("mostly accurate")
        else:
            explanations.append("factual concerns")

        # Claim support explanation
        if claim_support_score >= 0.8:
            explanations.append("well-supported claims")
        elif claim_support_score >= 0.6:
            explanations.append("adequately supported")
        else:
            explanations.append("weak claim support")

        # Specificity explanation
        if specificity_score >= 0.7:
            explanations.append("specific details")
        else:
            explanations.append("general statements")

        # Relevance explanation
        if relevance_score >= 0.8:
            explanations.append("directly relevant")
        elif relevance_score >= 0.6:
            explanations.append("mostly relevant")
        else:
            explanations.append("limited relevance")

        return f"Answer precision: {', '.join(explanations)}"
