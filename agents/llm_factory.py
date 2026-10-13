"""Deterministic mock-only supervisory response adapter."""
from .base import PHIGuard


class MockLLM:
    def __init__(self, system_name: str = "Radflow Sentinel Pro"):
        self.system_name = system_name

    def invoke(self, prompt: str) -> str:
        PHIGuard.assert_no_phi(prompt)
        return (
            f"[{self.system_name} mock response]: No clinical analysis was performed. "
            f"Query received: {prompt[:60]!r}."
        )


class LLMFactory:
    """Create implemented providers without silently substituting another provider."""

    @staticmethod
    def create(provider: str = "mock", system_name: str = "Radflow Sentinel Pro"):
        if str(provider).lower() in {"mock", "deterministic", "test"}:
            return MockLLM(system_name)
        raise ValueError(f"Unsupported model provider {provider!r}; only mock is implemented")
