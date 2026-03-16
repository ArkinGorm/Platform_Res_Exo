from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import Exercise, TestCase
from .serializers import ExerciseSerializer, ExerciseCreateSerializer, ExerciseListSerializer, TestCaseSerializer
from users.permissions import IsAdmin, IsAdminOrReadOnly

class ExerciseViewSet(viewsets.ModelViewSet):
    queryset = Exercise.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['difficulty', 'language', 'is_published']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'title']

    def get_serializer_class(self):
        if self.action == 'list':
            return ExerciseListSerializer
        elif self.action == 'create':
            return ExerciseCreateSerializer
        return ExerciseSerializer

    def get_permissions(self):
        """
        - Lecture: utilisateur authentifié
        - Création/modification/suppression: admin seulement
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdmin]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['get'])
    def test_cases(self, request, pk=None):
        """Récupérer les cas de test d'un exercice"""
        exercise = self.get_object()
        
        # Si l'utilisateur n'est pas admin, cacher les tests hidden
        if request.user.role == 'admin':
            test_cases = exercise.test_cases.all()
        else:
            test_cases = exercise.test_cases.filter(is_hidden=False)
            
        serializer = TestCaseSerializer(test_cases, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def published(self, request):
        """Liste des exercices publiés (pour les participants)"""
        exercises = self.get_queryset().filter(is_published=True)
        serializer = self.get_serializer(exercises, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAdmin])
    def unpublished(self, request):
        """Liste des exercices non publiés (pour les admins)"""
        exercises = self.get_queryset().filter(is_published=False)
        serializer = self.get_serializer(exercises, many=True)
        return Response(serializer.data)