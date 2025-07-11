# Copyright (c) 2025 ByteDance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""LLM Client wrapper for OpenAI, Anthropic, Azure, and OpenRouter APIs."""

from enum import Enum

from db_agent.tools.base import Tool as LocalTool
from mcp.types import Tool as MCPTool
from .base_client import BaseLLMClient
from .config import ModelParameters
from .llm_basics import LLMMessage, LLMResponse


class LLMProvider(Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE = "azure"
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"
    DOUBAO = "doubao"
    GOOGLE = "google"


class LLMClient:
    """Main LLM client that supports multiple providers."""

    def __init__(self, provider: str | LLMProvider, model_parameters: ModelParameters):
        if isinstance(provider, str):
            provider = LLMProvider(provider)

        self.provider: LLMProvider = provider
        self.model_parameters: ModelParameters = model_parameters

        match provider:
            case LLMProvider.OPENAI:
                from .openai_client import OpenAIClient

                self.client: BaseLLMClient = OpenAIClient(model_parameters)
            #case LLMProvider.OLLAMA:
            #    from .ollama_client import OllamaClient

            #    self.client = OllamaClient(model_parameters)

    def set_chat_history(self, messages: list[LLMMessage]) -> None:
        """Set the chat history."""
        self.client.set_chat_history(messages)

    def chat(
        self,
        messages: list[LLMMessage],
        #model_parameters: ModelParameters,
        local_tools: list[LocalTool] | None = None,
        mcp_tools: list[MCPTool] | None = None,
        reuse_history: bool = True,
    ) -> LLMResponse:
        """Send chat messages to the LLM."""
        return self.client.chat(messages, local_tools, mcp_tools, reuse_history)

    def supports_tool_calling(self, model_parameters: ModelParameters) -> bool:
        """Check if the current client supports tool calling."""
        return hasattr(
            self.client, "supports_tool_calling"
        ) and self.client.supports_tool_calling(model_parameters)
