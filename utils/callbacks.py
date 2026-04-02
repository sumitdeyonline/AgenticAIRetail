from typing import Any
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from dataclasses import dataclass

@dataclass
class TokenUsageAnalytics:
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    successful_requests: int = 0
    total_cost: float = 0.0

class TokenAnalyticsCallbackHandler(BaseCallbackHandler):
    """Callback to track token usage and cost dynamically."""
    
    def __init__(self, analytics_state: TokenUsageAnalytics, is_groq: bool = False):
        self.analytics = analytics_state
        self.is_groq = is_groq

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        self.analytics.successful_requests += 1
        
        if response.llm_output and "token_usage" in response.llm_output:
            usage = response.llm_output["token_usage"]
            p_tokens = usage.get("prompt_tokens", 0)
            c_tokens = usage.get("completion_tokens", 0)
            
            self.analytics.prompt_tokens += p_tokens
            self.analytics.completion_tokens += c_tokens
            self.analytics.total_tokens += usage.get("total_tokens", 0)
            
            if self.is_groq:
                # Groq typically uses open source models like Llama 3 which might be extremely cheap/free
                # Approximating roughly using standard open source api prices or 0
                self.analytics.total_cost += (p_tokens / 1000000) * 0.05 + (c_tokens / 1000000) * 0.08
            else:
                # Approximating gpt-4o-mini price
                self.analytics.total_cost += (p_tokens / 1000000) * 0.15 + (c_tokens / 1000000) * 0.60
