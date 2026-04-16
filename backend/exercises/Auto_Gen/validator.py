"""
Exercise validator — uses LLM to check coherence and clarity
before persisting a generated exercise to the database.
"""
import json
import logging
from dataclasses import dataclass, field

from langchain_core.language_models.chat_models import BaseChatModel

from .prompts import VALIDATION_PROMPT

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    is_valid: bool
    score: int = 0
    clarity_score: int = 0
    consistency_score: int = 0
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    # Minimum score to consider the exercise publishable
    # 65 est plus adapté aux modèles locaux (Ollama) qui scorent souvent entre 65-80
    PASS_THRESHOLD = 65

    @property
    def passed(self) -> bool:
        return self.is_valid and self.score >= self.PASS_THRESHOLD


class ExerciseValidator:
    """
    Validates a generated exercise dict using an LLM judge.
    """

    def __init__(self, llm: BaseChatModel):
        self.chain = VALIDATION_PROMPT | llm

    def validate(self, exercise: dict) -> ValidationResult:
        """
        Runs the validation prompt against the exercise.
        Returns a ValidationResult.
        """
        import json as _json

        test_cases_str = _json.dumps(exercise.get("test_cases", []), indent=2)

        try:
            response = self.chain.invoke({
                "title": exercise.get("title", ""),
                "language": exercise.get("language", ""),
                "difficulty": exercise.get("difficulty", ""),
                "description": exercise.get("description", ""),
                "solution": exercise.get("solution", ""),
                "test_cases": test_cases_str,
            })

            raw_text = response.content if hasattr(response, "content") else str(response)
            data = self._parse_json(raw_text)

            return ValidationResult(
                is_valid=data.get("is_valid", False),
                score=int(data.get("score", 0)),
                clarity_score=int(data.get("clarity_score", 0)),
                consistency_score=int(data.get("consistency_score", 0)),
                issues=data.get("issues", []),
                suggestions=data.get("suggestions", []),
                raw=data,
            )

        except Exception as exc:
            logger.exception("Validation LLM call failed: %s", exc)
            return ValidationResult(
                is_valid=False,
                score=0,
                issues=[f"Validation error: {str(exc)}"],
            )

    def _parse_json(self, text: str) -> dict:
        """Strips markdown fences and parses JSON."""
        import re
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            text = text.strip()
        # Extrait le bloc JSON si le LLM a ajouté du texte autour
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            text = match.group(0)
        return json.loads(text)
