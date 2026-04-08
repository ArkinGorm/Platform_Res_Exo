"""
Tâche Celery pour la génération asynchrone d'exercices.
Crée un Exercise + ses TestCase en base à partir du résultat du generator.
"""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=1, name="exercises.generate_exercise_task")
def generate_exercise_task(self, *, generation_request_id: int):
    """
    Tâche async — lance le pipeline de génération et sauvegarde le résultat.

    Crée :
      - Un Exercise (title, description, difficulty, language, solution, is_published)
      - Ses TestCase associés (input_data, expected_output, description, order)
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

    try:
        generator = ExerciseGenerator(
            provider=req.provider,
            model=req.model or None,
            temperature=req.temperature,
            validate=True,
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

            # --- Créer l'Exercise ---
            exercise = Exercise.objects.create(
                title=data.get("title", "Exercice généré"),
                description=data.get("description", ""),
                difficulty=data.get("difficulty", req.difficulty),
                language=data.get("language", req.language),
                solution=data.get("solution", ""),
                is_published=req.auto_publish,
                created_by=req.requested_by,
                # Champs IA (à ajouter via migration)
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

            logger.warning("Génération échouée pour la requête %d : %s", req.pk, result.error)

    except Exception as exc:
        logger.exception("Erreur inattendue dans generate_exercise_task : %s", exc)
        req.status = ExerciseGenerationRequest.Status.FAILED
        req.error_message = str(exc)
        req.completed_at = timezone.now()
        req.save(update_fields=["status", "error_message", "completed_at"])
        raise self.retry(exc=exc, countdown=10)
