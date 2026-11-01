"""Count text with an explicitly selected tokenizer, never silently estimate."""

import tiktoken


class TokenCounter:
    def __init__(self, encoding: str = "cl100k_base") -> None:
        try:
            self._encoding = tiktoken.get_encoding(encoding)
        except ValueError as exc:
            raise ValueError(f"Unknown tiktoken encoding: {encoding}") from exc
        self.name = encoding

    def count(self, text: str) -> int:
        # Logs may contain strings such as <|endoftext|>; these are plain data.
        return len(self._encoding.encode(text, disallowed_special=()))
