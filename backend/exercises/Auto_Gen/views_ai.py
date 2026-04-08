"""
Django REST Framework views for AI exercise generation.

Endpoints:
  POST   /api/exercises/generate/          → start generation task
  GET    /api/exercises/generate/<id>/     → poll status
  GET    /api/exercises/generate/providers/ → list available providers
  DELETE /api/exercises/generate/<id>/     → cancel pending request
"""
import logging

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
from exercises.Auto_Gen.tasks_ai import generate_exercise_task
from exercises.Auto_Gen.providers import list_providers

logger = logging.getLogger(__name__)


class GenerateExerciseView(APIView):
    """
    POST /api/exercises/generate/
    Enqueues a Celery task for AI exercise generation.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = GenerationRequestCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        # Create the tracking record
        gen_request = ExerciseGenerationRequest.objects.create(
            requested_by=request.user,
            **data,
        )

        # Dispatch Celery task
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
                "message": "Generation started. Poll /generate/<id>/ for status.",
            },
            status=status.HTTP_202_ACCEPTED,
        )


class GenerationRequestDetailView(APIView):
    """
    GET    /api/exercises/generate/<id>/   → poll status
    DELETE /api/exercises/generate/<id>/   → cancel if still pending
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

        # Revoke Celery task if it hasn't started yet
        if gen_request.celery_task_id:
            from celery.app.control import Control
            from django.conf import settings
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
    GET /api/exercises/generate/providers/
    Returns available AI providers for the frontend selector.
    """
    return Response(list_providers())


class UserGenerationHistoryView(APIView):
    """
    GET /api/exercises/generate/history/
    Returns the last 20 generation requests for the current user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        requests = ExerciseGenerationRequest.objects.filter(
            requested_by=request.user
        ).select_related("exercise")[:20]

        serializer = GenerationRequestStatusSerializer(requests, many=True)
        return Response(serializer.data)
