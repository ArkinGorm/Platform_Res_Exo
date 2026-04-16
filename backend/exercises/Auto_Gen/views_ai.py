"""
Django REST Framework views for AI exercise generation.

Endpoints:
  POST   /api/exercises/ai/generate/          → start generation task
  GET    /api/exercises/ai/generate/<id>/     → poll status
  GET    /api/exercises/ai/generate/providers/ → list available providers
  GET    /api/exercises/ai/generate/history/  → user generation history
  DELETE /api/exercises/ai/generate/<id>/     → cancel pending request

Mode d'exécution (settings.EXECUTION_MODE) :
  "local"  → run_generation() appelé directement (synchrone, sans Celery/Redis)
  "celery" → generate_exercise_task.delay() (asynchrone, nécessite Redis)
"""
import logging

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from exercises.models import ExerciseGenerationRequest
from exercises.Auto_Gen.serializers_ai import (
    GenerationRequestCreateSerializer,
    GenerationRequestStatusSerializer,
)
from exercises.Auto_Gen.tasks_ai import run_generation, generate_exercise_task
from exercises.Auto_Gen.providers import list_providers

logger = logging.getLogger(__name__)


def _get_execution_mode() -> str:
    """Retourne 'local' ou 'celery' selon la configuration."""
    return getattr(settings, "EXECUTION_MODE", "local").lower()


class GenerateExerciseView(APIView):
    """
    POST /api/exercises/ai/generate/

    Mode local  → exécution synchrone, réponse directe avec status=completed/failed.
    Mode celery → enqueue une tâche Celery, réponse avec status=pending.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = GenerationRequestCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        # Créer l'entrée de suivi
        gen_request = ExerciseGenerationRequest.objects.create(
            requested_by=request.user,
            **data,
        )

        mode = _get_execution_mode()

        if mode == "local":
            # ── Mode local : exécution synchrone ──────────────────────────
            # On retourne d'abord un 202 avec l'id, puis on exécute.
            # Cela permet au frontend de poller /generate/<id>/ normalement.
            import threading
            from django.db import connection

            pk = gen_request.pk

            def _run():
                # Django ferme la connexion DB à la fin du request principal.
                # On doit fermer explicitement ici pour forcer une nouvelle
                # connexion dans ce thread (Django en ouvrira une automatiquement).
                connection.close()
                try:
                    run_generation(pk)
                except Exception as exc:
                    logger.exception("Erreur lors de la génération locale : %s", exc)

            t = threading.Thread(target=_run, daemon=True)
            t.start()

            return Response(
                {
                    "id": gen_request.pk,
                    "status": gen_request.status,
                    "message": "Génération démarrée.",
                },
                status=status.HTTP_202_ACCEPTED,
            )

        else:
            # ── Mode celery : exécution asynchrone ────────────────────────
            task = generate_exercise_task.delay(
                generation_request_id=gen_request.pk
            )
            gen_request.celery_task_id = task.id
            gen_request.save(update_fields=["celery_task_id"])

            return Response(
                {
                    "id": gen_request.pk,
                    "status": gen_request.status,
                    "celery_task_id": task.id,
                    "message": "Génération démarrée. Interrogez /generate/<id>/ pour le statut.",
                },
                status=status.HTTP_202_ACCEPTED,
            )


class GenerationRequestDetailView(APIView):
    """
    GET    /api/exercises/ai/generate/<id>/   → poll status
    DELETE /api/exercises/ai/generate/<id>/   → cancel if still pending
    """
    permission_classes = [IsAuthenticated]

    def _get_request(self, pk, user):
        try:
            return ExerciseGenerationRequest.objects.get(pk=pk, requested_by=user)
        except ExerciseGenerationRequest.DoesNotExist:
            return None

    def get(self, request, pk):
        gen_request = self._get_request(pk, request.user)
        if not gen_request:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = GenerationRequestStatusSerializer(gen_request)
        return Response(serializer.data)

    def delete(self, request, pk):
        gen_request = self._get_request(pk, request.user)
        if not gen_request:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if gen_request.status != ExerciseGenerationRequest.Status.PENDING:
            return Response(
                {"detail": "Only pending requests can be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Révoquer la tâche Celery si elle existe (mode celery uniquement)
        if gen_request.celery_task_id and _get_execution_mode() == "celery":
            try:
                from config.celery import app as celery_app
                celery_app.control.revoke(gen_request.celery_task_id, terminate=False)
            except Exception as exc:
                logger.warning("Could not revoke task %s: %s", gen_request.celery_task_id, exc)

        gen_request.status = ExerciseGenerationRequest.Status.FAILED
        gen_request.error_message = "Cancelled by user."
        gen_request.save(update_fields=["status", "error_message"])

        return Response({"detail": "Request cancelled."})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_ai_providers(request):
    """
    GET /api/exercises/ai/generate/providers/
    Returns available AI providers + current execution mode.
    """
    return Response({
        "providers": list_providers(),
        "execution_mode": _get_execution_mode(),
        "ollama_base_url": getattr(settings, "OLLAMA_BASE_URL", ""),
    })


class UserGenerationHistoryView(APIView):
    """
    GET /api/exercises/ai/generate/history/
    Returns the last 20 generation requests for the current user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        requests_qs = ExerciseGenerationRequest.objects.filter(
            requested_by=request.user
        ).select_related("exercise")[:20]

        serializer = GenerationRequestStatusSerializer(requests_qs, many=True)
        return Response(serializer.data)
