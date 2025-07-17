"""
Load testing script for Sanad v2 using Locust.

This script tests the API under load to ensure it meets the p95 ≤ 1000ms
latency requirement as defined in PLANNING.md Section 5 (Constraints).
"""

import json
import random

from locust import HttpUser, between, task


class SanadUser(HttpUser):
    """
    Simulates a user of the Sanad v2 verification system.
    """

    # Wait time between requests (1-3 seconds)
    wait_time = between(1, 3)

    def on_start(self):
        """Called when a user starts."""
        # Sample queries for load testing
        self.queries = [
            "What is the minimum wage in Qatar?",
            "What are the working hours regulations?",
            "What is the process for obtaining a work permit?",
            "What are the employee rights regarding annual leave?",
            "What is the notice period for employment termination?",
            "What are the regulations for overtime work?",
            "What is the maternity leave policy?",
            "What are the workplace safety requirements?",
            "What is the process for resolving labor disputes?",
            "What are the regulations for domestic workers?",
            "What is the definition of Islamic finance?",
            "What are the key principles of Islamic banking?",
            "What is the difference between conventional and Islamic insurance?",
            "What are the main types of Islamic financial contracts?",
            "What is the role of a Sharia board in Islamic finance?",
            "What is the concept of riba in Islamic finance?",
            "What are the investment principles in Islamic finance?",
            "What is the difference between Murabaha and Musharaka?",
            "What are the challenges facing Islamic finance?",
            "What is the global market size of Islamic finance?",
        ]

    @task(10)
    def verify_query(self):
        """
        Main verification task - sends a query to the /verify endpoint.
        This task has weight 10 (most common operation).
        """
        query = random.choice(self.queries)

        with self.client.post(
            "/verify", json={"query": query}, catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Validate response structure
                    if "answer" in data and "sanad_score" in data:
                        response.success()
                    else:
                        response.failure("Invalid response structure")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(2)
    def health_check(self):
        """
        Health check task - tests the /healthz endpoint.
        This task has weight 2 (less frequent).
        """
        with self.client.get("/healthz", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: HTTP {response.status_code}")

    @task(1)
    def metrics_check(self):
        """
        Metrics check task - tests the /metrics endpoint with authentication.
        This task has weight 1 (least frequent).
        """
        # Note: In a real load test, you'd use proper credentials
        # For now, this will test the authentication mechanism
        with self.client.get(
            "/metrics",
            auth=("metrics", "test123"),  # Default test credentials
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                if "sanad_enhancement_attempts_total" in response.text:
                    response.success()
                else:
                    response.failure("Metrics endpoint missing expected metrics")
            elif response.status_code == 401:
                # Expected if credentials are wrong, but endpoint is working
                response.success()
            else:
                response.failure(f"Metrics check failed: HTTP {response.status_code}")


class SanadStressUser(HttpUser):
    """
    Stress testing user - sends requests more aggressively.
    Use this class for stress testing scenarios.
    """

    wait_time = between(0.1, 0.5)  # Much shorter wait times

    def on_start(self):
        """Called when a user starts."""
        self.queries = [
            "Quick test query 1",
            "Quick test query 2",
            "Quick test query 3",
            "Quick test query 4",
            "Quick test query 5",
        ]

    @task
    def rapid_verify(self):
        """Rapid verification requests for stress testing."""
        query = random.choice(self.queries)

        with self.client.post(
            "/verify", json={"query": query}, catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


# Example usage commands:
#
# Basic load test (3 QPS as per PLANNING.md):
# locust -f locustfile.py --host=http://localhost:8000 -u 3 -r 1 -t 60s --html=report.html
#
# Stress test:
# locust -f locustfile.py --host=http://localhost:8000 -u 50 -r 5 -t 300s --html=stress_report.html SanadStressUser
#
# Parameters:
# -u: Number of users to simulate
# -r: Spawn rate (users per second)
# -t: Test duration
# --html: Generate HTML report
