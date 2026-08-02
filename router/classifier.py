# router/classifier.py

from dataclasses import dataclass


@dataclass
class Classification:
    task: str
    reasoning_level: str


class PromptClassifier:

    def classify(self, prompt: str) -> Classification:

        text = prompt.lower()

        # Vision
        if any(word in text for word in [
            "image",
            "photo",
            "picture",
            "ocr",
            "diagram"
        ]):
            return Classification(
                task="vision",
                reasoning_level="medium"
            )

        # Coding
        if any(word in text for word in [
            "python",
            "javascript",
            "java",
            "code",
            "bug",
            "function",
            "sql",
            "api"
        ]):
            return Classification(
                task="coding",
                reasoning_level="high"
            )

        # Translation
        if any(word in text for word in [
            "translate",
            "translation",
            "french",
            "spanish",
            "german"
        ]):
            return Classification(
                task="translation",
                reasoning_level="low"
            )

        # Summarization
        if any(word in text for word in [
            "summarize",
            "summary",
            "shorten"
        ]):
            return Classification(
                task="summarization",
                reasoning_level="low"
            )

        return Classification(
            task="general",
            reasoning_level="medium"
        )