"""
ProvenanceAgent for Sanad v2.
Ensures citation presence and proper source attribution for regulatory compliance.
"""

import re
from typing import Any, Dict, List, Set, Tuple

from loguru import logger

try:
    from ..core.config import get_config
    from .base import AgentInput, AgentScore, BaseAgent
except ImportError:
    from agents.base import AgentInput, AgentScore, BaseAgent

    from core.config import get_config


class ProvenanceAgent(BaseAgent):
    """
    Agent that evaluates the provenance and traceability of information in the draft answer.
    Ensures proper citation, source attribution, and audit trail compliance.
    """

    def __init__(self):
        """Initialize the ProvenanceAgent."""
        super().__init__("ProvenanceAgent")
        self.config = get_config()

        # Citation patterns for detection
        self.citation_patterns = [
            r"\[(\d+)\]",  # [1], [2], etc.
            r"\[([^\]]+)\]",  # [doc_name], [Article 5], etc.
            r"\(([^)]+)\)",  # (source), (Article 5)
            r"according to ([^,.\n]+)",  # according to Qatar Labour Law
            r"as stated in ([^,.\n]+)",  # as stated in Article 5
            r"per ([^,.\n]+)",  # per Ministry guidelines
            r"Article (\d+)",  # Article 52
            r"Section (\d+)",  # Section 3
            r"Chapter (\d+)",  # Chapter 2
        ]

        # Source quality indicators
        self.source_quality_indicators = {
            "official": ["law", "government", "ministry", "official", "regulation"],
            "academic": ["research", "study", "analysis", "university", "institute"],
            "regulatory": ["decree", "policy", "guideline", "standard", "compliance"],
        }

        logger.info("Initialized ProvenanceAgent with citation detection patterns")

    async def evaluate(self, input_data: AgentInput) -> AgentScore:
        """
        Evaluate the provenance and citation quality of the draft answer.

        Args:
            input_data: Input containing question, draft answer, and passages

        Returns:
            AgentScore with provenance assessment
        """
        try:
            # Step 1: Detect citations in answer
            citations = self._detect_citations(input_data.draft_answer)

            # Step 2: Assess citation coverage
            coverage_score = self._assess_citation_coverage(
                input_data.draft_answer, input_data.passages
            )

            # Step 3: Evaluate source traceability
            traceability_score = self._evaluate_traceability(
                citations, input_data.passages
            )

            # Step 4: Check source diversity
            diversity_score = self._assess_source_diversity(input_data.passages)

            # Step 5: Validate source quality
            quality_score = self._validate_source_quality(input_data.passages)

            # Step 6: Compute composite provenance score
            composite_score = (
                coverage_score * 0.3  # 30% citation coverage
                + traceability_score * 0.25  # 25% traceability
                + diversity_score * 0.2  # 20% source diversity
                + quality_score * 0.25  # 25% source quality
            )

            # Step 7: Generate explanation
            explanation = self._generate_explanation(
                citations,
                coverage_score,
                traceability_score,
                diversity_score,
                quality_score,
                input_data.passages,
            )

            logger.debug(
                f"ProvenanceAgent: coverage={coverage_score:.3f}, "
                f"traceability={traceability_score:.3f}, "
                f"diversity={diversity_score:.3f}, "
                f"quality={quality_score:.3f}, "
                f"composite={composite_score:.3f}"
            )

            return AgentScore(
                score=composite_score,
                explanation=explanation,
                confidence=0.90,  # High confidence in provenance assessment
                agent_name=self.name,
            )

        except Exception as e:
            logger.error(f"ProvenanceAgent evaluation failed: {str(e)}")
            return AgentScore(
                score=0.5,
                explanation=f"Provenance evaluation failed: {str(e)}",
                confidence=0.0,
                agent_name=self.name,
            )

    def _detect_citations(self, answer: str) -> List[Dict[str, Any]]:
        """
        Detect and extract citations from the answer text.

        Args:
            answer: Draft answer text

        Returns:
            List of detected citations with metadata
        """
        citations = []

        for pattern_idx, pattern in enumerate(self.citation_patterns):
            matches = re.finditer(pattern, answer, re.IGNORECASE)

            for match in matches:
                citation = {
                    "text": match.group(0),
                    "reference": match.group(1) if match.groups() else match.group(0),
                    "start": match.start(),
                    "end": match.end(),
                    "pattern_type": pattern_idx,
                    "strength": self._assess_citation_strength(match.group(0)),
                }
                citations.append(citation)

        # Remove duplicates and sort by position
        unique_citations = []
        seen_positions = set()

        for citation in sorted(citations, key=lambda x: x["start"]):
            pos_key = (citation["start"], citation["end"])
            if pos_key not in seen_positions:
                unique_citations.append(citation)
                seen_positions.add(pos_key)

        logger.debug(f"Detected {len(unique_citations)} citations in answer")
        return unique_citations

    def _assess_citation_coverage(self, answer: str, passages: List[Any]) -> float:
        """
        Assess how well the answer cites the available sources.

        Args:
            answer: Draft answer text
            passages: Available source passages

        Returns:
            Citation coverage score (0.0 to 1.0)
        """
        if not passages:
            return 0.8  # No sources to cite

        # Count sentences that could benefit from citations
        sentences = re.split(r"[.!?]+", answer)
        factual_sentences = []

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10:  # Ignore very short sentences
                # Check if sentence contains factual claims
                if any(
                    indicator in sentence.lower()
                    for indicator in [
                        "is",
                        "are",
                        "must",
                        "shall",
                        "according to",
                        "states",
                        "requires",
                        "allows",
                        "prohibits",
                        "specifies",
                        "%",
                        "days",
                        "hours",
                        "article",
                        "section",
                        "law",
                        "regulation",
                    ]
                ):
                    factual_sentences.append(sentence)

        if not factual_sentences:
            return 0.8  # No factual claims to cite

        # Count citations
        citations = self._detect_citations(answer)
        citation_count = len(citations)

        # Calculate coverage ratio
        if len(factual_sentences) <= 2:
            # For short answers, expect at least 1 citation
            coverage_ratio = min(citation_count / 1, 1.0)
        else:
            # For longer answers, expect citation every 2-3 factual sentences
            expected_citations = max(1, len(factual_sentences) // 2)
            coverage_ratio = min(citation_count / expected_citations, 1.0)

        logger.debug(
            f"Citation coverage: {citation_count} citations for {len(factual_sentences)} factual sentences"
        )
        return coverage_ratio

    def _evaluate_traceability(
        self, citations: List[Dict[str, Any]], passages: List[Any]
    ) -> float:
        """
        Evaluate how well citations trace back to actual sources.

        Args:
            citations: Detected citations
            passages: Available source passages

        Returns:
            Traceability score (0.0 to 1.0)
        """
        if not citations:
            return 0.6  # No citations to trace

        if not passages:
            return 0.3  # Citations present but no sources available

        # Extract source identifiers from passages
        source_ids = set()
        for passage in passages:
            doc_id = getattr(passage, "doc_id", "").lower()
            source_ids.add(doc_id)

            # Also add variants
            if "labour_law" in doc_id:
                source_ids.update(["article", "law", "labour"])
            elif "research" in doc_id:
                source_ids.update(["study", "research", "report"])
            elif "qnds" in doc_id:
                source_ids.update(["strategy", "development", "national"])

        # Count traceable citations
        traceable_count = 0
        for citation in citations:
            reference = citation["reference"].lower()

            # Check if citation references available sources
            if any(source_id in reference for source_id in source_ids):
                traceable_count += 1
            # Also accept general legal references when law sources are available
            elif any(
                legal_term in reference for legal_term in ["article", "section", "law"]
            ) and any("law" in source_id for source_id in source_ids):
                traceable_count += 1

        traceability_ratio = traceable_count / len(citations) if citations else 0.6

        logger.debug(
            f"Traceability: {traceable_count}/{len(citations)} citations traceable to sources"
        )
        return min(max(traceability_ratio, 0.0), 1.0)

    def _assess_source_diversity(self, passages: List[Any]) -> float:
        """
        Assess the diversity of sources used.

        Args:
            passages: Available source passages

        Returns:
            Source diversity score (0.0 to 1.0)
        """
        if not passages:
            return 0.3

        # Group passages by source
        sources = set()
        source_types = set()

        for passage in passages:
            doc_id = getattr(passage, "doc_id", "").lower()
            sources.add(doc_id)

            # Categorize source type
            if any(
                indicator in doc_id
                for indicator in self.source_quality_indicators["official"]
            ):
                source_types.add("official")
            elif any(
                indicator in doc_id
                for indicator in self.source_quality_indicators["academic"]
            ):
                source_types.add("academic")
            elif any(
                indicator in doc_id
                for indicator in self.source_quality_indicators["regulatory"]
            ):
                source_types.add("regulatory")
            else:
                source_types.add("other")

        # Calculate diversity score
        num_sources = len(sources)
        num_types = len(source_types)

        # Base score from number of sources
        source_score = min(num_sources / 3, 1.0)  # Optimal is 3+ sources

        # Bonus for type diversity
        type_bonus = num_types * 0.1  # Up to 0.4 bonus for 4 types

        diversity_score = min(source_score + type_bonus, 1.0)

        logger.debug(f"Source diversity: {num_sources} sources, {num_types} types")
        return diversity_score

    def _validate_source_quality(self, passages: List[Any]) -> float:
        """
        Validate the quality and authority of sources.

        Args:
            passages: Available source passages

        Returns:
            Source quality score (0.0 to 1.0)
        """
        if not passages:
            return 0.3

        quality_scores = []

        for passage in passages:
            doc_id = getattr(passage, "doc_id", "").lower()
            category = getattr(passage, "category", "").lower()

            # Assess quality based on source characteristics
            base_quality = 0.5  # Default quality

            # Official/government sources get high scores
            if any(
                indicator in doc_id
                for indicator in self.source_quality_indicators["official"]
            ):
                base_quality = 0.9
            # Academic/research sources get good scores
            elif any(
                indicator in doc_id
                for indicator in self.source_quality_indicators["academic"]
            ):
                base_quality = 0.75
            # Regulatory sources get high scores
            elif any(
                indicator in doc_id
                for indicator in self.source_quality_indicators["regulatory"]
            ):
                base_quality = 0.85

            # Category-based adjustments
            if "official" in category:
                base_quality += 0.1
            elif "research" in category:
                base_quality += 0.05

            quality_scores.append(min(base_quality, 1.0))

        average_quality = sum(quality_scores) / len(quality_scores)

        logger.debug(
            f"Source quality: average {average_quality:.3f} from {len(passages)} sources"
        )
        return average_quality

    def _assess_citation_strength(self, citation_text: str) -> float:
        """
        Assess the strength/specificity of a citation.

        Args:
            citation_text: Citation text

        Returns:
            Citation strength score (0.0 to 1.0)
        """
        citation_lower = citation_text.lower()

        # Specific references get higher scores
        if re.search(r"article \d+", citation_lower) or re.search(
            r"section \d+", citation_lower
        ):
            return 0.9  # Very specific
        elif any(term in citation_lower for term in ["law", "regulation", "decree"]):
            return 0.8  # Good specificity
        elif any(term in citation_lower for term in ["according to", "as stated in"]):
            return 0.7  # Clear attribution
        elif re.search(r"\[\d+\]", citation_text):
            return 0.6  # Numbered reference
        else:
            return 0.5  # General reference

    def _generate_explanation(
        self,
        citations: List[Dict[str, Any]],
        coverage_score: float,
        traceability_score: float,
        diversity_score: float,
        quality_score: float,
        passages: List[Any],
    ) -> str:
        """
        Generate human-readable explanation of provenance assessment.

        Args:
            citations: Detected citations
            coverage_score: Citation coverage score
            traceability_score: Traceability score
            diversity_score: Source diversity score
            quality_score: Source quality score
            passages: Source passages

        Returns:
            Explanation string
        """
        explanations = []

        # Citation coverage
        citation_count = len(citations)
        if citation_count >= 2:
            explanations.append(f"well-cited ({citation_count} citations)")
        elif citation_count == 1:
            explanations.append("minimally cited (1 citation)")
        else:
            explanations.append("lacks citations")

        # Source traceability
        if traceability_score >= 0.8:
            explanations.append("traceable sources")
        elif traceability_score >= 0.6:
            explanations.append("mostly traceable")
        else:
            explanations.append("weak traceability")

        # Source diversity
        source_count = len(set(getattr(p, "doc_id", "unknown") for p in passages))
        if source_count >= 3:
            explanations.append("diverse sources")
        elif source_count >= 2:
            explanations.append("multiple sources")
        else:
            explanations.append("single source")

        # Source quality
        if quality_score >= 0.8:
            explanations.append("high-quality sources")
        elif quality_score >= 0.6:
            explanations.append("good sources")
        else:
            explanations.append("mixed source quality")

        return f"Provenance: {', '.join(explanations)}"
