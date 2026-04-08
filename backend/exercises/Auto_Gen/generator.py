"""
Avec generator.py j'orchestre la generation d'exercices. Ce dernier est adapté au modèle exercises pour un rendu optimal
"""
import json
import logging
from dataclasses import dataclass, field
from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel

from .prompts import GENERATION_PROMPT, REGENERATION_PROMPT
from .validator import ExerciseValidator, ValidationResult
from .providers import get_llm

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


@dataclass
class GenerationResult:
    success: bool
    exercise: Optional[dict] = None      # Prêt à être passé à _save_exercise()
    validation: Optional[ValidationResult] = None
    error: Optional[str] = None
    attempts: int = 0
    provider: str = ""
    model: str = ""


class ExerciseGenerator:
    """
    Génère un exercice complet compatible avec les modèles Exercise + TestCase.

    Args:
        provider    : "gemini" | "ollama"
        model       : override du modèle (ex: "gemini-1.5-pro", "qwen2.5-coder:7b")
        temperature : créativité du LLM
        validate    : activer la validation par LLM
        auto_fix    : tenter une correction si la validation échoue
    """

    def __init__(
        self,
        provider: str = "gemini",
        model: Optional[str] = None,
        temperature: float = 0.7,
        validate: bool = True,
        auto_fix: bool = True,
    ):
        self.provider = provider
        self.model = model
        self.validate = validate
        self.auto_fix = auto_fix

        llm_kwargs: dict = {"temperature": temperature}
        if model:
            llm_kwargs["model"] = model
        self.llm: BaseChatModel = get_llm(provider, **llm_kwargs)

        self.gen_chain = GENERATION_PROMPT | self.llm
        self.fix_chain = REGENERATION_PROMPT | self.llm
        self.validator = ExerciseValidator(self.llm)

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def generate(
        self,
        language: str,
        difficulty: str,
        topic: str,
        extra_instructions: str = "",
    ) -> GenerationResult:
        """
        Lance le pipeline complet.
        Retourne un GenerationResult dont exercise est un dict prêt pour tasks_ai.py.
        """
        attempts = 0

        # Étape 1 : génération initiale
        exercise, error = self._generate_once(language, difficulty, topic, extra_instructions)
        attempts += 1

        if error:
            return GenerationResult(success=False, error=error, attempts=attempts,
                                    provider=self.provider, model=self.model or "")

        # Injecter les métadonnées
        exercise["language"] = language
        exercise["difficulty"] = difficulty

        if not self.validate:
            return GenerationResult(success=True, exercise=exercise, attempts=attempts,
                                    provider=self.provider, model=self.model or "")

        # Étape 2 : validation
        validation = self.validator.validate(exercise)

        if validation.passed:
            return GenerationResult(success=True, exercise=exercise, validation=validation,
                                    attempts=attempts, provider=self.provider, model=self.model or "")

        logger.warning("Validation échouée (score=%d). Problèmes : %s", validation.score, validation.issues)

        if not self.auto_fix:
            return GenerationResult(
                success=False, exercise=exercise, validation=validation,
                error=f"Validation échouée (score={validation.score}): {'; '.join(validation.issues)}",
                attempts=attempts, provider=self.provider, model=self.model or "",
            )

        # Étape 3 : boucle de correction
        for retry in range(MAX_RETRIES):
            exercise, error = self._regenerate(exercise, validation)
            attempts += 1

            if error:
                logger.error("Correction %d échouée : %s", retry + 1, error)
                continue

            exercise["language"] = language
            exercise["difficulty"] = difficulty
            validation = self.validator.validate(exercise)

            if validation.passed:
                logger.info("Exercice validé après %d correction(s).", retry + 1)
                return GenerationResult(success=True, exercise=exercise, validation=validation,
                                        attempts=attempts, provider=self.provider, model=self.model or "")

            logger.warning("Correction %d : score=%d encore insuffisant.", retry + 1, validation.score)

        return GenerationResult(
            success=False, exercise=exercise, validation=validation,
            error=f"Échec après {attempts} tentatives. Dernier score : {validation.score}/100",
            attempts=attempts, provider=self.provider, model=self.model or "",
        )

    # ------------------------------------------------------------------
    # Méthodes privées
    # ------------------------------------------------------------------

    def _generate_once(self, language, difficulty, topic, extra_instructions):
        try:
            response = self.gen_chain.invoke({
                "language": language,
                "difficulty": difficulty,
                "topic": topic,
                "extra_instructions": extra_instructions or "Aucune",
            })
            text = response.content if hasattr(response, "content") else str(response)
            return self._parse_json(text), None
        except json.JSONDecodeError as exc:
            return None, f"JSON invalide retourné par le LLM : {exc}"
        except Exception as exc:
            logger.exception("Génération échouée : %s", exc)
            return None, str(exc)

    def _regenerate(self, exercise, validation):
        try:
            response = self.fix_chain.invoke({
                "original_exercise": json.dumps(exercise, ensure_ascii=False, indent=2),
                "issues": "\n".join(f"- {i}" for i in validation.issues),
                "suggestions": "\n".join(f"- {s}" for s in validation.suggestions),
            })
            text = response.content if hasattr(response, "content") else str(response)
            return self._parse_json(text), None
        except json.JSONDecodeError as exc:
            return None, f"JSON invalide lors de la correction : {exc}"
        except Exception as exc:
            logger.exception("Correction échouée : %s", exc)
            return None, str(exc)

    @staticmethod
    def _parse_json(text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])
        return json.loads(text)
