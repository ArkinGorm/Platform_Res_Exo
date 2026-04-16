"""
DRF serializers pour la génération IA d'exercices.
"""
from rest_framework import serializers
from exercises.models import ExerciseGenerationRequest

LANGUAGE_CHOICES = ["javascript", "python", "java"]
DIFFICULTY_CHOICES = ["facile", "moyen", "difficile"]


class GenerationRequestCreateSerializer(serializers.ModelSerializer):
    """Utilisé pour créer une nouvelle demande de génération (POST)."""

    provider = serializers.ChoiceField(choices=["gemini", "ollama"], default="gemini")
    model    = serializers.CharField(required=False, allow_blank=True, default="")
    language = serializers.ChoiceField(choices=LANGUAGE_CHOICES)
    difficulty = serializers.ChoiceField(choices=DIFFICULTY_CHOICES)
    topic    = serializers.CharField(min_length=5, max_length=300)
    extra_instructions = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=500
    )
    auto_publish = serializers.BooleanField(default=False)
    temperature  = serializers.FloatField(default=0.7, min_value=0.0, max_value=1.0)

    class Meta:
        model = ExerciseGenerationRequest
        fields = [
            "provider", "model", "language", "difficulty",
            "topic", "extra_instructions", "auto_publish", "temperature",
        ]


class GenerationRequestStatusSerializer(serializers.ModelSerializer):
    """
    Retourné par l'endpoint de polling.
    Inclut toutes les données de l'exercice généré pour que le frontend
    puisse pré-remplir ExerciseForm sans appel supplémentaire.
    """

    exercise_id       = serializers.SerializerMethodField()
    exercise_title    = serializers.SerializerMethodField()
    exercise_description = serializers.SerializerMethodField()
    exercise_solution    = serializers.SerializerMethodField()
    exercise_solution_template = serializers.SerializerMethodField()
    exercise_difficulty  = serializers.SerializerMethodField()
    exercise_language    = serializers.SerializerMethodField()
    exercise_test_cases  = serializers.SerializerMethodField()
    test_cases_count  = serializers.SerializerMethodField()
    duration_seconds  = serializers.SerializerMethodField()

    class Meta:
        model = ExerciseGenerationRequest
        fields = [
            "id", "status", "provider", "model",
            "language", "difficulty", "topic",
            "auto_publish", "attempts",
            "validation_score", "error_message",
            "created_at", "started_at", "completed_at",
            # Données de l'exercice généré (pour pré-remplir ExerciseForm)
            "exercise_id", "exercise_title", "exercise_description",
            "exercise_solution", "exercise_solution_template",
            "exercise_difficulty", "exercise_language", "exercise_test_cases",
            "test_cases_count", "duration_seconds",
            "celery_task_id",
        ]
        read_only_fields = fields

    def get_exercise_id(self, obj):
        return obj.exercise_id

    def get_exercise_title(self, obj):
        return obj.exercise.title if obj.exercise else None

    def get_exercise_description(self, obj):
        return obj.exercise.description if obj.exercise else None

    def get_exercise_solution(self, obj):
        return obj.exercise.solution if obj.exercise else None

    def get_exercise_solution_template(self, obj):
        if obj.exercise:
            # Retourne solution_template si le champ existe, sinon solution
            return getattr(obj.exercise, "solution_template", None) or obj.exercise.solution
        return None

    def get_exercise_difficulty(self, obj):
        return obj.exercise.difficulty if obj.exercise else None

    def get_exercise_language(self, obj):
        return obj.exercise.language if obj.exercise else None

    def get_exercise_test_cases(self, obj):
        if obj.exercise:
            return list(
                obj.exercise.test_cases.order_by("order").values(
                    "id", "input_data", "expected_output", "description", "order"
                )
            )
        return []

    def get_test_cases_count(self, obj):
        if obj.exercise:
            return obj.exercise.test_cases.count()
        return None

    def get_duration_seconds(self, obj):
        if obj.started_at and obj.completed_at:
            return round((obj.completed_at - obj.started_at).total_seconds(), 1)
        return None
