from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Submission
from .serializers import SubmissionSerializer, SubmissionCreateSerializer
from .tasks import execute_code_task

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
        """Soumettre une solution (asynchrone)"""
        serializer = SubmissionCreateSerializer(data=request.data)
        if serializer.is_valid():
            # Créer la soumission
            submission = Submission.objects.create(
                user=request.user,
                exercise=serializer.validated_data['exercise'],
                code=serializer.validated_data['code'],
                status='pending'
            )
            
            # Lancer la tâche Celery en arrière-plan
            task = execute_code_task.delay(submission.id)
            
            return Response({
                'submission_id': submission.id,
                'status': 'pending',
                'task_id': task.id,
                'message': 'Code envoyé pour exécution'
            }, status=status.HTTP_202_ACCEPTED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Vérifier le statut d'une soumission"""
        submission = self.get_object()
        return Response({
            'submission_id': submission.id,
            'status': submission.status,
            'execution_time': submission.execution_time,
            'submitted_at': submission.submitted_at
        })

    @action(detail=False, methods=['get'])
    def my_stats(self, request):
        """Statistiques personnelles"""
        submissions = Submission.objects.filter(user=request.user)
        
        total = submissions.count()
        passed = submissions.filter(status='passed').count()
        failed = submissions.filter(status='failed').count()
        pending = submissions.filter(status='pending').count()
        
        return Response({
            'total': total,
            'passed': passed,
            'failed': failed,
            'pending': pending,
            'success_rate': (passed / total * 100) if total > 0 else 0
        })