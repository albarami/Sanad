"""
Baseline LLM service for generating draft answers.
Uses OpenAI GPT-4o-mini as primary and Anthropic Claude as fallback.
"""

import asyncio
import time
from typing import Any, Dict, Optional

from anthropic import Anthropic, AnthropicError
from loguru import logger
from openai import OpenAI, OpenAIError
from pydantic import BaseModel

# Use absolute import when running as a module
try:
    from ..core.config import get_config
except ImportError:
    from core.config import get_config


class LLMResponse(BaseModel):
    """Response from the LLM service."""

    answer: str
    model: str
    provider: str
    tokens_used: int
    latency_ms: float


class BaselineLLM:
    """
    Baseline LLM service that generates draft answers.
    Implements fallback mechanism between OpenAI and Anthropic.
    """

    def __init__(self):
        """Initialize the LLM service with configuration."""
        self.config = get_config()

        # Initialize OpenAI client
        self.openai_client = None
        if self.config.openai_api_key:
            self.openai_client = OpenAI(api_key=self.config.openai_api_key)
        else:
            logger.warning("OpenAI API key not found in configuration")

        # Initialize Anthropic client
        self.anthropic_client = None
        if self.config.anthropic_api_key:
            self.anthropic_client = Anthropic(api_key=self.config.anthropic_api_key)
        else:
            logger.warning("Anthropic API key not found in configuration")

        # Ensure at least one provider is available
        if not self.openai_client and not self.anthropic_client:
            raise ValueError(
                "No LLM provider configured. Please set OPENAI_API_KEY or ANTHROPIC_API_KEY"
            )

    def _create_system_prompt(self) -> str:
        """
        Create the system prompt for the LLM.

        Returns:
            System prompt string
        """
        return (
            "You are a helpful assistant providing accurate, concise answers. "
            "Your responses should be factual and to the point. "
            "Limit your response to 150 tokens maximum. "
            "If you're unsure about something, say so clearly."
        )

    async def _call_openai(self, question: str) -> LLMResponse:
        """
        Call OpenAI API to generate a response.

        Args:
            question: The user's question

        Returns:
            LLMResponse object

        Raises:
            OpenAIError: If the API call fails
        """
        if not self.openai_client:
            raise OpenAIError("OpenAI client not initialized")

        start_time = time.time()

        try:
            response = self.openai_client.chat.completions.create(
                model=self.config.llm.openai.model,
                messages=[
                    {"role": "system", "content": self._create_system_prompt()},
                    {"role": "user", "content": question},
                ],
                temperature=self.config.llm.openai.temperature,
                max_tokens=self.config.llm.openai.max_tokens,
                timeout=self.config.llm.openai.timeout,
            )

            latency_ms = (time.time() - start_time) * 1000

            return LLMResponse(
                answer=response.choices[0].message.content.strip(),
                model=response.model,
                provider="openai",
                tokens_used=response.usage.total_tokens,
                latency_ms=latency_ms,
            )

        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise

    async def _call_anthropic(self, question: str) -> LLMResponse:
        """
        Call Anthropic API to generate a response.

        Args:
            question: The user's question

        Returns:
            LLMResponse object

        Raises:
            AnthropicError: If the API call fails
        """
        if not self.anthropic_client:
            raise AnthropicError("Anthropic client not initialized")

        start_time = time.time()

        try:
            response = self.anthropic_client.messages.create(
                model=self.config.llm.anthropic.model,
                system=self._create_system_prompt(),
                messages=[{"role": "user", "content": question}],
                temperature=self.config.llm.anthropic.temperature,
                max_tokens=self.config.llm.anthropic.max_tokens,
                timeout=self.config.llm.anthropic.timeout,
            )

            latency_ms = (time.time() - start_time) * 1000

            # Extract text content from response
            answer = ""
            if response.content:
                if isinstance(response.content, list):
                    answer = response.content[0].text if response.content else ""
                else:
                    answer = response.content

            return LLMResponse(
                answer=answer.strip(),
                model=response.model,
                provider="anthropic",
                tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                latency_ms=latency_ms,
            )

        except Exception as e:
            logger.error(f"Anthropic API error: {str(e)}")
            raise

    async def draft(self, question: str) -> LLMResponse:
        """
        Generate a draft answer using the configured LLM provider.
        Implements fallback mechanism if primary provider fails.

        Args:
            question: The user's question

        Returns:
            LLMResponse object with the generated answer
        """
        # Determine primary and fallback providers
        primary = self.config.llm.primary_provider
        fallback = self.config.llm.fallback_provider

        # Try primary provider first
        if primary == "openai" and self.openai_client:
            try:
                logger.debug(f"Calling OpenAI for question: {question[:50]}...")
                return await self._call_openai(question)
            except Exception as e:
                logger.warning(f"Primary provider (OpenAI) failed: {str(e)}")
                if fallback == "anthropic" and self.anthropic_client:
                    logger.info("Falling back to Anthropic")
                    return await self._call_anthropic(question)
                else:
                    raise

        elif primary == "anthropic" and self.anthropic_client:
            try:
                logger.debug(f"Calling Anthropic for question: {question[:50]}...")
                return await self._call_anthropic(question)
            except Exception as e:
                logger.warning(f"Primary provider (Anthropic) failed: {str(e)}")
                if fallback == "openai" and self.openai_client:
                    logger.info("Falling back to OpenAI")
                    return await self._call_openai(question)
                else:
                    raise

        else:
            raise ValueError(f"No available provider for primary: {primary}")

    def draft_sync(self, question: str) -> LLMResponse:
        """
        Synchronous wrapper for the draft method.

        Args:
            question: The user's question

        Returns:
            LLMResponse object with the generated answer
        """
        return asyncio.run(self.draft(question))


if __name__ == "__main__":
    # Test the baseline LLM
    import os

    # Set a test API key if needed
    if not os.getenv("OPENAI_API_KEY"):
        print("Please set OPENAI_API_KEY environment variable to test")
        exit(1)

    llm = BaselineLLM()

    test_questions = [
        "What is the capital of France?",
        "Explain quantum computing in simple terms.",
        "What are the main benefits of exercise?",
    ]

    for question in test_questions:
        print(f"\nQuestion: {question}")
        try:
            response = llm.draft_sync(question)
            print(f"Answer: {response.answer}")
            print(f"Provider: {response.provider} ({response.model})")
            print(
                f"Tokens: {response.tokens_used}, Latency: {response.latency_ms:.2f}ms"
            )
        except Exception as e:
            print(f"Error: {str(e)}")
