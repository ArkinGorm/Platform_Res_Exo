from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Submission, TestResult
from exercises.models import Exercise, TestCase
from users.models import User
from .serializers import SubmissionSerializer, SubmissionCreateSerializer
from users.permissions import IsAdmin, IsOwnerOrReadOnly
import json

class SubmissionViewSet(viewsets.ModelViewSet):
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer

    def get_permissions(self):
        """
        - Lecture: propriétaire ou admin
        - Création: utilisateur authentifié
        """
        if self.action in ['retrieve', 'list']:
            permission_classes = [IsAuthenticated]
        elif self.action == 'create':
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAdmin]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """Filtre les soumissions selon le rôle"""
        user = self.request.user
        
        if user.role == 'admin':
            # Les admins voient tout
            return Submission.objects.all()
        else:
            # Les participants voient leurs propres soumissions
            return Submission.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'])
    def submit(self, request):
        """Soumettre une solution"""
        serializer = SubmissionCreateSerializer(data=request.data)
        if serializer.is_valid():
            exercise = serializer.validated_data['exercise']
            code = serializer.validated_data['code']
            
            # Vérifier que l'exercice est publié
            if not exercise.is_published and request.user.role != 'admin':
                return Response(
                    {'error': 'Cet exercice n\'est pas encore publié'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Créer la soumission
            submission = Submission.objects.create(
                user=request.user,
                exercise=exercise,
                code=code,
                status='pending'
            )

            # Simuler l'exécution des tests
            test_results = []
            all_passed = True

            for test_case in exercise.test_cases.all():
                # Simulation simple
                passed = 'return' in code
                
                result = TestResult.objects.create(
                    submission=submission,
                    test_case=test_case,
                    passed=passed,
                    actual_output="Résultat simulé",
                    error_message="" if passed else "Le code ne compile pas"
                )
                test_results.append(result)
                if not passed:
                    all_passed = False

            # Mettre à jour le statut
            submission.status = 'passed' if all_passed else 'failed'
            submission.save()

            # Retourner les résultats
            result_serializer = SubmissionSerializer(submission)
            return Response(result_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def my_submissions(self, request):
        """Mes soumissions (pour participants)"""
        submissions = Submission.objects.filter(user=request.user)
        serializer = self.get_serializer(submissions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAdmin])
    def stats(self, request):
        """Statistiques globales (pour admin)"""
        total_submissions = Submission.objects.count()
        total_users = User.objects.count()
        total_exercises = Exercise.objects.count()
        
        submissions_by_status = {
            'pending': Submission.objects.filter(status='pending').count(),
            'passed': Submission.objects.filter(status='passed').count(),
            'failed': Submission.objects.filter(status='failed').count(),
        }
        
        return Response({
            'total_submissions': total_submissions,
            'total_users': total_users,
            'total_exercises': total_exercises,
            'submissions_by_status': submissions_by_status
        })