from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from .models import Submission
from .serializers import SubmissionSerializer, SubmissionCreateSerializer
from .tasks import execute_code_task
from .sandbox import CodeSandbox
from exercises.models import Exercise
import logging

logger = logging.getLogger(__name__)


def _use_celery() -> bool:
    return getattr(settings, "EXECUTION_MODE", "local").lower() == "celery"


class SubmissionViewSet(viewsets.ModelViewSet):
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'admin':
            return Submission.objects.all()
        return Submission.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    def submit(self, request):
        """Soumettre une solution — async (celery) ou sync (local)"""
        serializer = SubmissionCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        submission = Submission.objects.create(
            user=request.user,
            exercise=serializer.validated_data['exercise'],
            code=serializer.validated_data['code'],
            status='pending'
        )

        if _use_celery():
            task = execute_code_task.delay(submission.id)
            return Response({
                'submission_id': submission.id,
                'status': 'pending',
                'task_id': task.id,
                'message': 'Code envoyé pour exécution',
            }, status=status.HTTP_202_ACCEPTED)
        else:
            # Mode local : exécution synchrone dans un thread (comme views_ai.py)
            import threading
            from django.db import connection as db_conn

            pk = submission.id

            def _run():
                db_conn.close()
                try:
                    from .tasks import _run_submission
                    _run_submission(pk)
                except Exception as exc:
                    logger.exception("Erreur exécution locale submission %s : %s", pk, exc)

            threading.Thread(target=_run, daemon=True).start()

            return Response({
                'submission_id': submission.id,
                'status': 'pending',
                'message': 'Exécution démarrée (mode local)',
            }, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=['post'])
    def run(self, request):
        """
        Exécution libre — entrée fournie par l'utilisateur.
        Aucune sauvegarde en base, aucun test case officiel.
        Body attendu : { exercise_id, code, user_input }
        """
        exercise_id = request.data.get('exercise_id')
        code        = request.data.get('code', '').strip()
        user_input  = request.data.get('user_input', '')

        if not exercise_id or not code:
            return Response(
                {'error': 'exercise_id et code sont requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            exercise = Exercise.objects.get(id=exercise_id)
        except Exercise.DoesNotExist:
            return Response({'error': 'Exercice introuvable'}, status=status.HTTP_404_NOT_FOUND)

        # Construire un script qui appelle le code avec l'entrée libre
        language = exercise.language
        if language == 'javascript':
            run_script = f"""
{code}
try {{
    const input = {user_input if user_input.strip() else 'undefined'};
    const args = Array.isArray(input) ? input : (input !== undefined ? [input] : []);
    const res = solution(...args);
    if (res !== undefined) process.stdout.write(String(res));
    process.exit(0);
}} catch (e) {{
    process.stderr.write(String(e.message));
    process.exit(1);
}}
"""
        else:  # python
            run_script = f"""
{code}
import sys
try:
    input_data = {user_input if user_input.strip() else 'None'}
    if input_data is None:
        args = []
    elif isinstance(input_data, (list, tuple)):
        args = list(input_data)
    else:
        args = [input_data]
    res = solution(*args)
    if res is not None:
        sys.stdout.write(str(res))
    sys.exit(0)
except Exception as e:
    sys.stderr.write(str(e))
    sys.exit(1)
"""

        sandbox = CodeSandbox(language=language)
        output, error = sandbox.execute(run_script, timeout=10)

        return Response({
            'output': output or '',
            'error':  error  or '',
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Vérifier le statut d'une soumission"""
        submission = self.get_object()
        serializer = SubmissionSerializer(submission)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_stats(self, request):
        """Statistiques personnelles"""
        submissions = Submission.objects.filter(user=request.user)
        total   = submissions.count()
        passed  = submissions.filter(status='passed').count()
        failed  = submissions.filter(status='failed').count()
        pending = submissions.filter(status='pending').count()

        return Response({
            'total':        total,
            'passed':       passed,
            'failed':       failed,
            'pending':      pending,
            'success_rate': (passed / total * 100) if total > 0 else 0
        })
