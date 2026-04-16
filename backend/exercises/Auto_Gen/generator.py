"""
Avec generator.py j'orchestre la generation d'exercices. Ce dernier est adapté au modèle exercises pour un rendu optimal.
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

    Le JSON retourné par le LLM contient deux champs distincts :
      - solution          : code complet et fonctionnel (référence pour les tests)
      - solution_template : squelette avec TODO pour l'étudiant

    Stratégie d'économie de quota Gemini :
      - La validation LLM (ExerciseValidator) est désactivée pour Gemini :
        elle consomme un appel API supplémentaire pour un exercice déjà de
        haute qualité. On fait confiance à la génération directe.
      - La température par défaut est 0.4 (contre 0.7) pour réduire les
        sorties non-JSON et donc les retries coûteux.
      - Le prompt a été condensé pour minimiser les tokens d'entrée.
      - Ollama garde la validation car les appels sont gratuits et les
        modèles locaux plus petits nécessitent plus de contrôle.

    Args:
        provider    : "gemini" | "ollama"
        model       : override du modèle (ex: "gemini-2.5-flash", "qwen2.5-coder:1.5b")
        temperature : créativité du LLM (défaut 0.4 pour Gemini, 0.7 pour Ollama)
        validate    : activer la validation par LLM (auto = False si Gemini)
        auto_fix    : tenter une correction si la validation échoue
    """

    def __init__(
        self,
        provider: str = "gemini",
        model: Optional[str] = None,
        temperature: float = None,  # None = auto selon provider
        validate: bool = None,       # None = auto selon provider
        auto_fix: bool = True,
    ):
        self.provider = provider

        # ── Économie quota : Gemini ne valide pas, température plus basse ──
        is_gemini = provider == "gemini"
        self.validate  = (not is_gemini) if validate is None else validate
        auto_temp      = 0.4 if is_gemini else 0.7
        self.auto_fix  = auto_fix
        self.model     = model

        llm_kwargs: dict = {"temperature": temperature if temperature is not None else auto_temp}
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
        Le dict contient toujours les clés : title, description, solution,
        solution_template, test_cases, language, difficulty.
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

        # Garantir que chaque test a une description non vide
        exercise = self._ensure_test_descriptions(exercise)

        # Garantir la présence de solution_template
        exercise = self._ensure_solution_template(exercise)

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
            exercise = self._ensure_test_descriptions(exercise)
            exercise = self._ensure_solution_template(exercise)
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
    def _ensure_test_descriptions(exercise: dict) -> dict:
        """
        S'assure que chaque test case a une description non vide.
        Génère un fallback lisible si le LLM a omis le champ.
        """
        for i, tc in enumerate(exercise.get("test_cases", []), start=1):
            if not tc.get("description", "").strip():
                inp = tc.get("input_data", "")
                out = tc.get("expected_output", "")
                if i == 1:
                    tc["description"] = "Cas nominal de base"
                else:
                    tc["description"] = f"Test {i} — entrée : {str(inp)[:40]}, attendu : {str(out)[:40]}"
        return exercise

    @staticmethod
    def _ensure_solution_template(exercise: dict) -> dict:
        """
        S'assure que solution_template est présent.
        Si le LLM ne l'a pas fourni, on utilise solution comme fallback
        (l'admin pourra le modifier dans ExerciseForm).
        """
        if not exercise.get("solution_template", "").strip():
            exercise["solution_template"] = exercise.get("solution", "")
        return exercise

    @staticmethod
    def _parse_json(text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])
        return json.loads(text)
