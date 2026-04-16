"""
Tâche Celery pour la génération asynchrone d'exercices.
Crée un Exercise + ses TestCase en base à partir du résultat du generator.

En mode local (EXECUTION_MODE=local), la fonction run_generation() peut être
appelée directement depuis views_ai.py, sans passer par Celery/Redis.
"""
import logging
from celery import shared_task
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Logique de génération — appelable directement OU depuis la tâche Celery
# ---------------------------------------------------------------------------

def run_generation(generation_request_id: int) -> None:
    """
    Exécute le pipeline complet de génération et sauvegarde le résultat.

    Peut être appelée :
      - Directement (mode local, synchrone) depuis views_ai.py
      - Depuis generate_exercise_task (mode Celery, asynchrone)

    Crée :
      - Un Exercise (title, description, difficulty, language, solution,
                     solution_template, is_published)
      - Ses TestCase associés (input_data, expected_output, description, order)

    Champs sauvegardés :
      - solution          → solution complète exécutable (reference pour les tests)
      - solution_template → squelette avec TODO (affiché à l'étudiant dans ExerciseForm)
    """
    from exercises.models import Exercise, TestCase, ExerciseGenerationRequest
    from exercises.Auto_Gen.generator import ExerciseGenerator

    # --- Récupérer la requête ---
    try:
        req = ExerciseGenerationRequest.objects.get(pk=generation_request_id)
    except ExerciseGenerationRequest.DoesNotExist:
        logger.error("ExerciseGenerationRequest %d introuvable.", generation_request_id)
        return

    # --- Marquer comme démarré ---
    req.status = ExerciseGenerationRequest.Status.RUNNING
    req.started_at = timezone.now()
    req.save(update_fields=["status", "started_at"])
    logger.info(
        "Génération démarrée pour la requête %d (provider=%s)",
        generation_request_id, req.provider
    )

    try:
        generator = ExerciseGenerator(
            provider=req.provider,
            model=req.model or None,   # None = le provider utilise son défaut
            temperature=req.temperature,
            # Ne PAS forcer validate=True — laisser ExerciseGenerator décider
            # selon le provider (Gemini → False pour économiser les quotas,
            # Ollama → True car les appels sont gratuits).
            validate=None,
            auto_fix=True,
        )

        result = generator.generate(
            language=req.language,
            difficulty=req.difficulty,
            topic=req.topic,
            extra_instructions=req.extra_instructions,
        )

        req.attempts = result.attempts

        if result.success:
            data = result.exercise

            # solution complète (référence pour faire tourner les tests)
            solution_ref = data.get("solution", "")

            # solution_template = squelette TODO pour l'étudiant
            # Si le LLM n'a pas fourni le champ, on utilise solution_ref comme fallback
            solution_template = data.get("solution_template", solution_ref)

            # --- Créer l'Exercise ---
            exercise = Exercise.objects.create(
                title=data.get("title", "Exercice généré"),
                description=data.get("description", ""),
                difficulty=data.get("difficulty", req.difficulty),
                language=data.get("language", req.language),
                solution=solution_ref,
                solution_template=solution_template,
                is_published=req.auto_publish,
                created_by=req.requested_by,
                ai_generated=True,
                ai_provider=req.provider,
                ai_model=req.model or "",
            )

            # --- Créer les TestCase ---
            test_cases_data = data.get("test_cases", [])
            test_cases = [
                TestCase(
                    exercise=exercise,
                    input_data=str(tc.get("input_data", "")),
                    expected_output=str(tc.get("expected_output", "")),
                    description=tc.get("description", ""),
                    order=idx,
                )
                for idx, tc in enumerate(test_cases_data)
            ]
            if test_cases:
                TestCase.objects.bulk_create(test_cases)

            # --- Mettre à jour la requête ---
            req.status = ExerciseGenerationRequest.Status.COMPLETED
            req.exercise = exercise
            req.validation_score = result.validation.score if result.validation else None
            req.completed_at = timezone.now()
            req.save(update_fields=[
                "status", "exercise", "validation_score",
                "completed_at", "attempts",
            ])

            logger.info(
                "Exercice généré : pk=%d, tests=%d, score=%s",
                exercise.pk, len(test_cases), req.validation_score,
            )

        else:
            req.status = ExerciseGenerationRequest.Status.FAILED
            req.error_message = result.error or "Erreur inconnue"
            req.completed_at = timezone.now()
            req.save(update_fields=["status", "error_message", "completed_at", "attempts"])

            logger.warning(
                "Génération échouée pour la requête %d : %s", req.pk, result.error
            )

    except Exception as exc:
        logger.exception("Erreur inattendue dans run_generation : %s", exc)
        req.status = ExerciseGenerationRequest.Status.FAILED
        req.error_message = str(exc)
        req.completed_at = timezone.now()
        req.save(update_fields=["status", "error_message", "completed_at"])
        raise


# ---------------------------------------------------------------------------
# Tâche Celery — wrapper autour de run_generation()
# ---------------------------------------------------------------------------

@shared_task(bind=True, max_retries=1, name="exercises.generate_exercise_task")
def generate_exercise_task(self, *, generation_request_id: int):
    """
    Tâche Celery asynchrone — délègue à run_generation().
    Utilisée uniquement quand EXECUTION_MODE=celery.
    """
    try:
        run_generation(generation_request_id)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=10)
