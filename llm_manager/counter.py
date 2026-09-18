"""Token counting using tiktoken + HuggingFace tokenizers."""

from __future__ import annotations

from typing import Optional

try:
    import tiktoken
except ImportError:  # pragma: no cover
    tiktoken = None

try:
    from tokenizers import Tokenizer as HFTokenizer
except ImportError:  # pragma: no cover
    HFTokenizer = None  # type: ignore

from utils.logger import get_logger

log = get_logger("token_counter")

MODEL_ENCODERS = {
    "meta/llama-3.1-8b-instruct": "gpt-4",
    "google/gemma-2-9b-it": "gpt-4",
    "microsoft/phi-3-mini-4k-instruct": "gpt-4",
    "nvidia/nemotron-4-340b-instruct": "gpt-4",
}

_SIZE_RATIOS = {
    "8b": 0.3,
    "9b": 0.3,
    "2b": 0.2,
    "340b": 0.4,
    "7b": 0.3,
    "12b": 0.3,
}


def _size_category(model: str) -> str:
    lowered = model.lower()
    for size in ("340b", "12b", "9b", "8b", "7b", "5b", "3b", "2b"):
        if size in lowered:
            return size
    return "8b"


class TokenCounter:
    """Multi-model token counting using tiktoken (and tokenizers fallback)."""

    def __init__(self) -> None:
        self._encoders: dict[str, tiktoken.Encoding] = {}

    def _encoder(self, model: str):
        enc_name = MODEL_ENCODERS.get(model, "gpt-4")
        if enc_name not in self._encoders:
            if tiktoken is None:
                self._encoders[enc_name] = None
            else:
                try:
                    self._encoders[enc_name] = tiktoken.encoding_for_model(enc_name)
                except (KeyError, Exception):
                    self._encoders[enc_name] = tiktoken.get_encoding("cl100k_base")
        return self._encoders[enc_name]

    def count(self, text: str, model: str = "gpt-4") -> int:
        encoder = self._encoder(model)
        if encoder is None:
            return max(1, len(text) // 4)
        try:
            return len(encoder.encode(text))
        except Exception:
            return max(1, len(text) // 4)

    def count_messages(self, messages: list[dict], model: str = "gpt-4") -> int:
        encoder = self._encoder(model)
        if encoder is None:
            total = 0
            for m in messages:
                content = m.get("content", "")
                if isinstance(content, str):
                    total += max(1, len(content) // 4)
                total += 4
            return total + 3
        try:
            return sum(
                self._msg_tokens(m, encoder) for m in messages
            ) + 3
        except Exception:
            return self.count(" ".join(m.get("content", "") for m in messages), model)

    @staticmethod
    def _msg_tokens(msg: dict, encoder) -> int:
        content = msg.get("content", "")
        if isinstance(content, list):
            content = "".join(
                p.get("text", "") for p in content if isinstance(p, dict)
            )
        if not isinstance(content, str):
            content = str(content)
        return len(encoder.encode(content)) + 4

    def estimate_response(self, input_tokens: int, model: str) -> int:
        ratio = _SIZE_RATIOS.get(_size_category(model), 0.3)
        return int(input_tokens * ratio)

    def estimate(self, messages: list[dict], model: str = "gpt-4") -> int:
        return self.count_messages(messages, model)
