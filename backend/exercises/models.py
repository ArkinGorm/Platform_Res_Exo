from django.db import models
from django.conf import settings
from .Auto_Gen.models_ai import ExerciseGenerationRequest


class Exercise(models.Model):
    DIFFICULTY_CHOICES = (
        ('facile', 'Facile'),
        ('moyen', 'Moyen'),
        ('difficile', 'Difficile'),
    )
    LANGUAGE_CHOICES = (
        ('javascript', 'JavaScript'),
        ('python', 'Python'),
        ('java', 'Java'),
    )

    title        = models.CharField(max_length=200)
    description  = models.TextField()
    difficulty   = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='facile')
    language     = models.CharField(max_length=20, choices=LANGUAGE_CHOICES, default='javascript')

    # Solution complète (référence serveur — fait tourner les tests, non visible par l'étudiant)
    solution          = models.TextField(blank=True)

    # Squelette avec TODO affiché à l'étudiant dans l'éditeur de code
    # Rempli uniquement pour les exercices générés par IA ; vide = identique à solution
    solution_template = models.TextField(blank=True)

    created_by   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    is_published = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)

    # Métadonnées IA
    ai_generated = models.BooleanField(default=False)
    ai_provider  = models.CharField(max_length=50, blank=True)
    ai_model     = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.title


class TestCase(models.Model):
    exercise        = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='test_cases')
    input_data      = models.TextField()
    expected_output = models.TextField()
    description     = models.CharField(max_length=255, blank=True)
    order           = models.IntegerField(default=0)
