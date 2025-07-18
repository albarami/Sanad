"""
Benchmark script for Sanad v2 accuracy testing.

This script evaluates the system's accuracy against a predefined benchmark dataset
to ensure it meets the quality gate of ≥85% legal-hit rate as defined in PLANNING.md.
"""

import asyncio
import csv
import json
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import requests

# Add backend to path for imports
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from core.config import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Result of a single benchmark test."""

    question: str
    expected_answer: str
    actual_answer: str
    category: str
    difficulty: str
    is_correct: bool
    confidence_score: float
    response_time_ms: float
    sanad_score: float


class BenchmarkRunner:
    """
    Runs accuracy benchmarks against the Sanad v2 API.
    """

    def __init__(self, api_base_url: str = "http://localhost:8000"):
        """
        Initialize the benchmark runner.

        Args:
            api_base_url: Base URL of the Sanad API
        """
        self.api_base_url = api_base_url
        self.config = get_config()

        # Benchmark parameters
        self.benchmark_file = Path("data/benchmarks/accuracy_benchmark.csv")
        self.results_dir = Path("data/benchmarks/results")
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # Accuracy thresholds from PLANNING.md
        self.target_accuracy = 0.85  # 85% legal-hit rate
        self.target_latency_ms = 1000  # p95 ≤ 1000ms

        logger.info("✅ BenchmarkRunner initialized")

    def load_benchmark_dataset(self) -> List[Dict[str, str]]:
        """
        Load the benchmark dataset from CSV.

        Returns:
            List of benchmark questions and expected answers
        """
        if not self.benchmark_file.exists():
            raise FileNotFoundError(f"Benchmark file not found: {self.benchmark_file}")

        questions = []
        with open(self.benchmark_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                questions.append(row)

        logger.info(f"Loaded {len(questions)} benchmark questions")
        return questions

    def call_verify_api(self, question: str) -> Tuple[Dict, float]:
        """
        Call the /verify API endpoint with a question.

        Args:
            question: The question to ask

        Returns:
            Tuple of (response_data, response_time_ms)
        """
        start_time = time.time()

        try:
            response = requests.post(
                f"{self.api_base_url}/api/verify", json={"question": question}, timeout=60
            )

            response_time_ms = (time.time() - start_time) * 1000

            if response.status_code == 200:
                return response.json(), response_time_ms
            else:
                logger.error(f"API error {response.status_code}: {response.text}")
                return {"error": f"HTTP {response.status_code}"}, response_time_ms

        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            logger.error(f"API call failed: {e}")
            return {"error": str(e)}, response_time_ms

    def evaluate_answer(self, expected: str, actual: str, category: str) -> bool:
        """
        Evaluate if the actual answer matches the expected answer.

        This is a simplified evaluation. In production, this would use
        more sophisticated NLP techniques or human evaluation.

        Args:
            expected: Expected answer
            actual: Actual answer from the system
            category: Question category

        Returns:
            True if the answer is considered correct
        """
        # Simple keyword-based evaluation
        expected_lower = expected.lower()
        actual_lower = actual.lower()

        # Extract key terms from expected answer
        key_terms = []

        # Category-specific key term extraction
        if category == "labor_market":
            # Look for specific numbers, laws, or key concepts
            import re

            numbers = re.findall(r"\d+", expected)
            key_terms.extend(numbers)

            # Key labor terms
            labor_terms = [
                "wage",
                "hours",
                "leave",
                "notice",
                "overtime",
                "maternity",
                "safety",
                "permit",
            ]
            for term in labor_terms:
                if term in expected_lower:
                    key_terms.append(term)

        elif category == "finance":
            # Key Islamic finance terms
            finance_terms = [
                "riba",
                "sharia",
                "murabaha",
                "musharaka",
                "takaful",
                "halal",
                "haram",
            ]
            for term in finance_terms:
                if term in expected_lower:
                    key_terms.append(term)

        # Check if key terms are present in actual answer
        if not key_terms:
            # Fallback: simple substring matching
            return any(
                word in actual_lower for word in expected_lower.split() if len(word) > 3
            )

        # Calculate match ratio
        matches = sum(1 for term in key_terms if term in actual_lower)
        match_ratio = matches / len(key_terms) if key_terms else 0

        # Consider correct if at least 60% of key terms match
        return match_ratio >= 0.6

    def run_single_benchmark(self, question_data: Dict[str, str]) -> BenchmarkResult:
        """
        Run a single benchmark test.

        Args:
            question_data: Dictionary with question, expected_answer, etc.

        Returns:
            BenchmarkResult object
        """
        question = question_data["question"]
        expected_answer = question_data["expected_answer"]
        category = question_data["category"]
        difficulty = question_data["difficulty"]

        logger.info(f"Testing: {question[:50]}...")

        # Call the API
        response_data, response_time_ms = self.call_verify_api(question)

        # Extract answer and scores
        if "error" in response_data:
            actual_answer = f"ERROR: {response_data['error']}"
            confidence_score = 0.0
            sanad_score = 0.0
            is_correct = False
        else:
            actual_answer = response_data.get("answer", "No answer provided")
            confidence_score = response_data.get("confidence", 0.0)
            sanad_score = response_data.get("sanad_score", 0.0)

            # Evaluate correctness
            is_correct = self.evaluate_answer(expected_answer, actual_answer, category)

        return BenchmarkResult(
            question=question,
            expected_answer=expected_answer,
            actual_answer=actual_answer,
            category=category,
            difficulty=difficulty,
            is_correct=is_correct,
            confidence_score=confidence_score,
            response_time_ms=response_time_ms,
            sanad_score=sanad_score,
        )

    def run_full_benchmark(self) -> List[BenchmarkResult]:
        """
        Run the full benchmark suite.

        Returns:
            List of BenchmarkResult objects
        """
        logger.info("🚀 Starting full benchmark run...")

        # Load benchmark dataset
        questions = self.load_benchmark_dataset()

        # Run all benchmarks
        results = []
        for i, question_data in enumerate(questions, 1):
            logger.info(f"Running benchmark {i}/{len(questions)}")

            result = self.run_single_benchmark(question_data)
            results.append(result)

            # Small delay to avoid overwhelming the API
            time.sleep(0.1)

        logger.info("✅ Benchmark run completed")
        return results

    def analyze_results(self, results: List[BenchmarkResult]) -> Dict:
        """
        Analyze benchmark results and generate statistics.

        Args:
            results: List of BenchmarkResult objects

        Returns:
            Dictionary with analysis results
        """
        total_questions = len(results)
        correct_answers = sum(1 for r in results if r.is_correct)
        accuracy = correct_answers / total_questions if total_questions > 0 else 0

        # Response time statistics
        response_times = [r.response_time_ms for r in results]
        avg_response_time = (
            sum(response_times) / len(response_times) if response_times else 0
        )
        p95_response_time = (
            sorted(response_times)[int(0.95 * len(response_times))]
            if response_times
            else 0
        )

        # Category breakdown
        category_stats = {}
        for result in results:
            cat = result.category
            if cat not in category_stats:
                category_stats[cat] = {"total": 0, "correct": 0}
            category_stats[cat]["total"] += 1
            if result.is_correct:
                category_stats[cat]["correct"] += 1

        # Calculate category accuracies
        for cat in category_stats:
            stats = category_stats[cat]
            stats["accuracy"] = (
                stats["correct"] / stats["total"] if stats["total"] > 0 else 0
            )

        # Difficulty breakdown
        difficulty_stats = {}
        for result in results:
            diff = result.difficulty
            if diff not in difficulty_stats:
                difficulty_stats[diff] = {"total": 0, "correct": 0}
            difficulty_stats[diff]["total"] += 1
            if result.is_correct:
                difficulty_stats[diff]["correct"] += 1

        # Calculate difficulty accuracies
        for diff in difficulty_stats:
            stats = difficulty_stats[diff]
            stats["accuracy"] = (
                stats["correct"] / stats["total"] if stats["total"] > 0 else 0
            )

        analysis = {
            "overall_accuracy": accuracy,
            "total_questions": total_questions,
            "correct_answers": correct_answers,
            "target_accuracy": self.target_accuracy,
            "meets_accuracy_target": accuracy >= self.target_accuracy,
            "avg_response_time_ms": avg_response_time,
            "p95_response_time_ms": p95_response_time,
            "target_latency_ms": self.target_latency_ms,
            "meets_latency_target": p95_response_time <= self.target_latency_ms,
            "category_breakdown": category_stats,
            "difficulty_breakdown": difficulty_stats,
        }

        return analysis

    def save_results(self, results: List[BenchmarkResult], analysis: Dict) -> None:
        """
        Save benchmark results to files.

        Args:
            results: List of BenchmarkResult objects
            analysis: Analysis dictionary
        """
        timestamp = time.strftime("%Y%m%d_%H%M%S")

        # Save detailed results
        results_file = self.results_dir / f"benchmark_results_{timestamp}.json"
        results_data = []
        for result in results:
            results_data.append(
                {
                    "question": result.question,
                    "expected_answer": result.expected_answer,
                    "actual_answer": result.actual_answer,
                    "category": result.category,
                    "difficulty": result.difficulty,
                    "is_correct": result.is_correct,
                    "confidence_score": result.confidence_score,
                    "response_time_ms": result.response_time_ms,
                    "sanad_score": result.sanad_score,
                }
            )

        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)

        # Save analysis
        analysis_file = self.results_dir / f"benchmark_analysis_{timestamp}.json"
        with open(analysis_file, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)

        logger.info(f"Results saved to {results_file}")
        logger.info(f"Analysis saved to {analysis_file}")

    def print_summary(self, analysis: Dict) -> None:
        """
        Print a summary of benchmark results.

        Args:
            analysis: Analysis dictionary
        """
        print("\n" + "=" * 60)
        print("📊 SANAD V2 BENCHMARK RESULTS")
        print("=" * 60)

        print(f"\n🎯 Overall Performance:")
        print(
            f"Accuracy: {analysis['overall_accuracy']:.1%} ({analysis['correct_answers']}/{analysis['total_questions']})"
        )
        print(f"Target:   {analysis['target_accuracy']:.1%}")
        print(
            f"Status:   {'✅ PASS' if analysis['meets_accuracy_target'] else '❌ FAIL'}"
        )

        print(f"\n⚡ Response Time:")
        print(f"Average:  {analysis['avg_response_time_ms']:.0f}ms")
        print(f"P95:      {analysis['p95_response_time_ms']:.0f}ms")
        print(f"Target:   {analysis['target_latency_ms']}ms")
        print(
            f"Status:   {'✅ PASS' if analysis['meets_latency_target'] else '❌ FAIL'}"
        )

        print(f"\n📂 Category Breakdown:")
        for category, stats in analysis["category_breakdown"].items():
            print(
                f"{category:15} {stats['accuracy']:.1%} ({stats['correct']}/{stats['total']})"
            )

        print(f"\n📈 Difficulty Breakdown:")
        for difficulty, stats in analysis["difficulty_breakdown"].items():
            print(
                f"{difficulty:15} {stats['accuracy']:.1%} ({stats['correct']}/{stats['total']})"
            )

        # Overall pass/fail
        overall_pass = (
            analysis["meets_accuracy_target"] and analysis["meets_latency_target"]
        )
        print(f"\n🏆 Overall Result: {'✅ PASS' if overall_pass else '❌ FAIL'}")
        print("=" * 60)


def main():
    """Main entry point."""
    runner = BenchmarkRunner()

    try:
        # Run benchmarks
        results = runner.run_full_benchmark()

        # Analyze results
        analysis = runner.analyze_results(results)

        # Save results
        runner.save_results(results, analysis)

        # Print summary
        runner.print_summary(analysis)

        # Exit with appropriate code
        # Only fail on accuracy, latency is a performance warning
        if analysis["meets_accuracy_target"]:
            if not analysis["meets_latency_target"]:
                logger.warning(f"Latency target not met: {analysis['p95_response_time_ms']:.0f}ms > {analysis['target_latency_ms']}ms")
            sys.exit(0)  # Success if accuracy met
        else:
            sys.exit(1)  # Failure only if accuracy not met

    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
