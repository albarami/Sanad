"""
DomainAgent-LabourLaw for Sanad v2.
Specialized evaluation for Qatar labour law context and regulatory compliance.
"""

import asyncio
import re
from typing import Any, Dict, List, Set, Tuple

from loguru import logger

try:
    from ..core.baseline_llm import BaselineLLM
    from ..core.config import get_config
    from .base import AgentInput, AgentScore, BaseAgent
except ImportError:
    from agents.base import AgentInput, AgentScore, BaseAgent
    from core.baseline_llm import BaselineLLM
    from core.config import get_config


class DomainLabourAgent(BaseAgent):
    """
    Domain-specific agent for Qatar Labour Law evaluation.
    Combines regex pattern matching with LLM analysis for specialized legal context.
    """

    def __init__(self):
        """Initialize the DomainLabourAgent."""
        super().__init__("DomainAgent-LabourLaw")
        self.config = get_config()
        self.llm = BaselineLLM()

        # Qatar Labour Law specific patterns and rules
        self.labour_law_patterns = {
            # Key legal concepts
            "employment_contract": [
                r"employment contract",
                r"work contract",
                r"عقد العمل",
                r"عقد التوظيف",
            ],
            "probation_period": [
                r"probation(?:ary)?\s+period",
                r"trial period",
                r"فترة التجربة",
                r"فترة الاختبار",
            ],
            "termination": [
                r"terminat(?:e|ion)",
                r"dismiss(?:al)?",
                r"end(?:ing)?\s+(?:of\s+)?employment",
                r"إنهاء",
                r"فصل",
                r"إقالة",
            ],
            "notice_period": [
                r"notice\s+period",
                r"advance\s+notice",
                r"مدة الإشعار",
                r"فترة الإخطار",
            ],
            "working_hours": [
                r"working\s+hours?",
                r"work(?:ing)?\s+time",
                r"ساعات العمل",
                r"وقت العمل",
            ],
            "overtime": [
                r"overtime",
                r"extra\s+hours?",
                r"العمل الإضافي",
                r"ساعات إضافية",
            ],
            "annual_leave": [
                r"annual\s+leave",
                r"vacation",
                r"holiday",
                r"الإجازة السنوية",
                r"عطلة",
            ],
            "sick_leave": [r"sick\s+leave", r"medical\s+leave", r"إجازة مرضية"],
            "wages": [
                r"wages?",
                r"salary",
                r"compensation",
                r"pay(?:ment)?",
                r"راتب",
                r"أجر",
                r"مرتب",
            ],
            "rights": [r"rights?", r"entitlement", r"حقوق", r"استحقاق"],
            "obligations": [
                r"obligation",
                r"duties",
                r"responsibilities",
                r"واجبات",
                r"التزامات",
            ],
        }

        # Qatar-specific legal references
        self.qatar_legal_refs = {
            "labour_law": [
                r"qatar(?:i)?\s+labo?ur\s+law",
                r"law\s+no\.?\s*14",
                r"قانون العمل القطري",
                r"القانون رقم 14",
            ],
            "ministry_labour": [
                r"ministry\s+of\s+(?:administrative\s+development\s+)?labo?ur",
                r"وزارة العمل",
                r"وزارة التنمية الإدارية والعمل",
            ],
            "articles": [r"article\s+(\d+)", r"المادة\s+(\d+)"],
        }

        # Common legal values and timeframes
        self.legal_values = {
            "probation_max": "6 months",
            "notice_periods": ["1 week", "1 month", "2 months", "3 months"],
            "working_hours_max": "8 hours/day",
            "working_hours_week": "48 hours/week",
            "overtime_rate": "125%",
            "overtime_weekend": "150%",
            "annual_leave_min": "21 days",
        }

        logger.info("Initialized DomainLabourAgent with Qatar labour law patterns")

    async def evaluate(self, input_data: AgentInput) -> AgentScore:
        """
        Evaluate the answer for Qatar labour law domain-specific accuracy.

        Args:
            input_data: Input containing question, draft answer, and passages

        Returns:
            AgentScore with domain-specific assessment
        """
        try:
            # Step 1: Check domain relevance
            relevance_score = self._assess_domain_relevance(
                input_data.question, input_data.draft_answer
            )

            # Step 2: Validate legal patterns and terms
            pattern_score = self._validate_legal_patterns(input_data.draft_answer)

            # Step 3: Check Qatar-specific context
            qatar_context_score = self._check_qatar_context(
                input_data.draft_answer, input_data.passages
            )

            # Step 4: Validate legal values and timeframes
            values_score = await self._validate_legal_values(input_data)

            # Step 5: Assess regulatory compliance language
            compliance_score = self._assess_compliance_language(input_data.draft_answer)

            # Step 6: Compute composite domain score
            composite_score = (
                relevance_score * 0.25  # 25% domain relevance
                + pattern_score * 0.20  # 20% legal pattern accuracy
                + qatar_context_score * 0.25  # 25% Qatar-specific context
                + values_score * 0.20  # 20% legal values accuracy
                + compliance_score * 0.10  # 10% compliance language
            )

            # Step 7: Generate explanation
            explanation = self._generate_explanation(
                relevance_score,
                pattern_score,
                qatar_context_score,
                values_score,
                compliance_score,
            )

            logger.debug(
                f"DomainLabourAgent: relevance={relevance_score:.3f}, "
                f"patterns={pattern_score:.3f}, qatar_context={qatar_context_score:.3f}, "
                f"values={values_score:.3f}, compliance={compliance_score:.3f}, "
                f"composite={composite_score:.3f}"
            )

            return AgentScore(
                score=composite_score,
                explanation=explanation,
                confidence=0.85,  # High confidence in domain assessment
                agent_name=self.name,
            )

        except Exception as e:
            logger.error(f"DomainLabourAgent evaluation failed: {str(e)}")
            return AgentScore(
                score=0.5,
                explanation=f"Domain evaluation failed: {str(e)}",
                confidence=0.0,
                agent_name=self.name,
            )

    def _assess_domain_relevance(self, question: str, answer: str) -> float:
        """
        Assess if the question and answer are relevant to labour law domain.

        Args:
            question: Original question
            answer: Draft answer

        Returns:
            Domain relevance score (0.0 to 1.0)
        """
        combined_text = (question + " " + answer).lower()

        # Count matches for each category
        total_matches = 0
        categories_matched = 0

        for category, patterns in self.labour_law_patterns.items():
            category_matches = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, combined_text, re.IGNORECASE))
                category_matches += matches
                total_matches += matches

            if category_matches > 0:
                categories_matched += 1

        # Calculate relevance score
        if total_matches == 0:
            return 0.3  # Low relevance

        # Base score from total matches
        base_score = min(total_matches * 0.1, 0.7)

        # Bonus for multiple categories (indicates comprehensive coverage)
        category_bonus = min(categories_matched * 0.1, 0.3)

        relevance_score = base_score + category_bonus

        logger.debug(
            f"Domain relevance: {total_matches} matches across {categories_matched} categories"
        )
        return min(max(relevance_score, 0.0), 1.0)

    def _validate_legal_patterns(self, answer: str) -> float:
        """
        Validate legal terminology and pattern usage in the answer.

        Args:
            answer: Draft answer text

        Returns:
            Legal pattern validation score (0.0 to 1.0)
        """
        answer_lower = answer.lower()

        # Check for proper legal terminology
        proper_terms = 0
        total_legal_concepts = 0

        for category, patterns in self.labour_law_patterns.items():
            for pattern in patterns:
                if re.search(pattern, answer_lower, re.IGNORECASE):
                    total_legal_concepts += 1
                    # Check if it's used in proper legal context
                    if self._is_proper_legal_usage(pattern, answer_lower):
                        proper_terms += 1

        # Check for Qatar-specific legal references
        qatar_refs = 0
        for category, patterns in self.qatar_legal_refs.items():
            for pattern in patterns:
                if re.search(pattern, answer_lower, re.IGNORECASE):
                    qatar_refs += 1

        # Calculate pattern score
        if total_legal_concepts == 0:
            return 0.6  # No legal concepts mentioned

        proper_usage_ratio = proper_terms / total_legal_concepts
        qatar_bonus = min(qatar_refs * 0.1, 0.2)  # Up to 0.2 bonus for Qatar refs

        pattern_score = proper_usage_ratio + qatar_bonus

        logger.debug(
            f"Legal patterns: {proper_terms}/{total_legal_concepts} proper usage, {qatar_refs} Qatar refs"
        )
        return min(max(pattern_score, 0.0), 1.0)

    def _check_qatar_context(self, answer: str, passages: List[Any]) -> float:
        """
        Check if the answer properly addresses Qatar-specific labour law context.

        Args:
            answer: Draft answer text
            passages: Source passages

        Returns:
            Qatar context score (0.0 to 1.0)
        """
        # Check for Qatar-specific indicators in answer
        qatar_indicators = [
            r"qatar(?:i)?",
            r"qr",
            r"doha",
            r"gcc",
            r"قطر",
            r"قطري",
            r"الدوحة",
        ]

        answer_lower = answer.lower()
        qatar_mentions = sum(
            1
            for pattern in qatar_indicators
            if re.search(pattern, answer_lower, re.IGNORECASE)
        )

        # Check if passages are from Qatar sources
        qatar_sources = 0
        total_sources = 0

        for passage in passages:
            doc_id = getattr(passage, "doc_id", "").lower()
            total_sources += 1

            if any(
                indicator in doc_id for indicator in ["qatar", "labour_law", "qnds"]
            ):
                qatar_sources += 1

        # Calculate context score
        answer_context = min(
            qatar_mentions * 0.3, 0.6
        )  # Up to 0.6 from answer mentions

        if total_sources > 0:
            source_context = (
                qatar_sources / total_sources
            ) * 0.4  # Up to 0.4 from sources
        else:
            source_context = 0.2  # Default when no sources

        context_score = answer_context + source_context

        logger.debug(
            f"Qatar context: {qatar_mentions} answer mentions, {qatar_sources}/{total_sources} Qatar sources"
        )
        return min(max(context_score, 0.0), 1.0)

    async def _validate_legal_values(self, input_data: AgentInput) -> float:
        """
        Validate specific legal values and timeframes mentioned in the answer.

        Args:
            input_data: Input data including question, answer, and passages

        Returns:
            Legal values validation score (0.0 to 1.0)
        """
        try:
            # Extract numerical values and timeframes from answer
            values_found = self._extract_legal_values(input_data.draft_answer)

            if not values_found:
                return 0.7  # No specific values to validate

            # Build validation prompt
            prompt = self._build_values_validation_prompt(
                input_data.question,
                input_data.draft_answer,
                values_found,
                input_data.passages,
            )

            # Call LLM to validate values
            response = await self.llm.draft(prompt)
            validation_result = response.answer.lower()

            # Parse validation result
            if "accurate" in validation_result and "correct" in validation_result:
                return 0.9
            elif (
                "mostly accurate" in validation_result
                or "largely correct" in validation_result
            ):
                return 0.8
            elif "partially accurate" in validation_result:
                return 0.6
            elif "inaccurate" in validation_result or "incorrect" in validation_result:
                return 0.3
            else:
                return 0.7  # Default when unclear

        except Exception as e:
            logger.warning(f"Legal values validation failed: {str(e)}")
            return 0.7

    def _assess_compliance_language(self, answer: str) -> float:
        """
        Assess the use of appropriate compliance and regulatory language.

        Args:
            answer: Draft answer text

        Returns:
            Compliance language score (0.0 to 1.0)
        """
        answer_lower = answer.lower()

        # Positive compliance indicators
        positive_indicators = [
            r"according to",
            r"as per",
            r"in compliance with",
            r"pursuant to",
            r"shall",
            r"must",
            r"required",
            r"mandatory",
            r"stipulated",
            r"governed by",
            r"subject to",
            r"in accordance with",
        ]

        # Negative indicators (vague or non-compliant language)
        negative_indicators = [
            r"might",
            r"maybe",
            r"possibly",
            r"generally",
            r"usually",
            r"often",
            r"sometimes",
            r"could be",
            r"may be",
        ]

        positive_count = sum(
            1 for pattern in positive_indicators if re.search(pattern, answer_lower)
        )
        negative_count = sum(
            1 for pattern in negative_indicators if re.search(pattern, answer_lower)
        )

        # Calculate compliance score
        base_score = 0.5
        positive_boost = min(positive_count * 0.1, 0.4)
        negative_penalty = min(negative_count * 0.1, 0.3)

        compliance_score = base_score + positive_boost - negative_penalty

        logger.debug(
            f"Compliance language: {positive_count} positive, {negative_count} negative indicators"
        )
        return min(max(compliance_score, 0.0), 1.0)

    def _is_proper_legal_usage(self, pattern: str, text: str) -> bool:
        """
        Check if a legal term is used in proper legal context.

        Args:
            pattern: Legal pattern to check
            text: Text containing the pattern

        Returns:
            True if used properly, False otherwise
        """
        # Find the pattern in text and check surrounding context
        matches = list(re.finditer(pattern, text, re.IGNORECASE))

        for match in matches:
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            context = text[start:end].lower()

            # Check for proper legal context indicators
            legal_context_indicators = [
                "according to",
                "as per",
                "law",
                "article",
                "section",
                "regulation",
                "provision",
                "clause",
                "statute",
                "legal",
                "employment",
                "employer",
                "employee",
                "contract",
            ]

            if any(indicator in context for indicator in legal_context_indicators):
                return True

        return False

    def _extract_legal_values(self, answer: str) -> List[Dict[str, Any]]:
        """
        Extract numerical values and timeframes from the answer.

        Args:
            answer: Answer text

        Returns:
            List of extracted values with metadata
        """
        values = []

        # Patterns for different types of legal values
        value_patterns = {
            "time_period": r"(\d+)\s+(days?|weeks?|months?|years?)",
            "percentage": r"(\d+(?:\.\d+)?)\s*%",
            "hours": r"(\d+)\s+hours?",
            "money": r"(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:QAR|riyal|dollar|\$)",
            "article_ref": r"[Aa]rticle\s+(\d+)",
            "section_ref": r"[Ss]ection\s+(\d+)",
        }

        for value_type, pattern in value_patterns.items():
            matches = re.finditer(pattern, answer, re.IGNORECASE)
            for match in matches:
                values.append(
                    {
                        "type": value_type,
                        "value": match.group(0),
                        "number": match.group(1),
                        "position": match.start(),
                    }
                )

        return values

    def _build_values_validation_prompt(
        self,
        question: str,
        answer: str,
        values: List[Dict[str, Any]],
        passages: List[Any],
    ) -> str:
        """
        Build prompt for validating legal values against sources.

        Args:
            question: Original question
            answer: Draft answer
            values: Extracted values to validate
            passages: Source passages

        Returns:
            Validation prompt string
        """
        values_text = "\n".join([f"- {v['value']} ({v['type']})" for v in values])

        passages_text = "\n\n".join(
            [
                f"Source {i+1}: {getattr(p, 'text', str(p))[:300]}..."
                for i, p in enumerate(passages[:3])
            ]
        )

        prompt = f"""Validate the legal values and timeframes in this answer against Qatar Labour Law sources.

QUESTION: {question}

ANSWER: {answer}

SPECIFIC VALUES TO VALIDATE:
{values_text}

QATAR LABOUR LAW SOURCES:
{passages_text}

Task: Check if the numerical values, timeframes, and legal references are accurate according to Qatar Labour Law.

Respond with one of:
- "Accurate and correct - values match Qatar Labour Law"
- "Mostly accurate - minor discrepancies only"
- "Partially accurate - some values correct"
- "Inaccurate - values contradict Qatar Labour Law"

Validation result:"""

        return prompt

    def _generate_explanation(
        self,
        relevance_score: float,
        pattern_score: float,
        qatar_context_score: float,
        values_score: float,
        compliance_score: float,
    ) -> str:
        """
        Generate human-readable explanation of domain assessment.

        Args:
            relevance_score: Domain relevance score
            pattern_score: Legal pattern score
            qatar_context_score: Qatar context score
            values_score: Legal values score
            compliance_score: Compliance language score

        Returns:
            Explanation string
        """
        explanations = []

        # Domain relevance
        if relevance_score >= 0.7:
            explanations.append("highly relevant to labour law")
        elif relevance_score >= 0.5:
            explanations.append("moderately relevant to labour law")
        else:
            explanations.append("limited labour law relevance")

        # Qatar context
        if qatar_context_score >= 0.7:
            explanations.append("Qatar-specific context")
        elif qatar_context_score >= 0.5:
            explanations.append("some Qatar context")
        else:
            explanations.append("general context only")

        # Legal patterns and compliance
        if pattern_score >= 0.7 and compliance_score >= 0.7:
            explanations.append("proper legal terminology")
        elif pattern_score >= 0.5 or compliance_score >= 0.5:
            explanations.append("adequate legal language")
        else:
            explanations.append("informal language")

        # Values accuracy
        if values_score >= 0.8:
            explanations.append("accurate legal values")
        elif values_score >= 0.6:
            explanations.append("mostly accurate values")
        else:
            explanations.append("questionable values")

        return f"Labour law domain: {', '.join(explanations)}"
