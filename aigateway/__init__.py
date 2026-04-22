"""Official Python SDK for AIgateway.

For chat, embeddings, images, STT, TTS, moderation — use the `openai` package
with ``base_url='https://api.aigateway.sh/v1'``. AIgateway is drop-in.

This SDK covers the aggregator-native surface: async jobs, sub-accounts,
evals, replays, signed file URLs, and webhook signature verification.
"""

from .client import AIgateway, AsyncAIgateway, AIgatewayError
from .webhook import verify_webhook

__all__ = [
    "AIgateway",
    "AsyncAIgateway",
    "AIgatewayError",
    "verify_webhook",
    "__version__",
]

__version__ = "0.1.2"
