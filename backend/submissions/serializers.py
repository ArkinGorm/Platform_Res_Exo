from rest_framework import serializers
from .models import Submission, TestResult
from exercises.models import Exercise


class TestResultSerializer(serializers.ModelSerializer):
    # Champs du test_case lié (entrée + sortie attendue)
    input        = serializers.SerializerMethodField()
    expected     = serializers.SerializerMethodField()
    # Renommage pour homogénéité côté front
    output       = serializers.CharField(source='actual_output', read_only=True)

    class Meta:
        model  = TestResult
        fields = [
            'id',
            'test_case',
            'passed',
            'input',           # entrée du test case
            'expected',        # sortie attendue
            'output',          # sortie obtenue (= actual_output)
            'actual_output',   # conservé pour compatibilité
            'error_message',   # stderr
            'execution_time',  # temps en ms (si le champ existe)
        ]

    def get_input(self, obj):
        """Retourne l'input du test_case associé."""
        if obj.test_case:
            return obj.test_case.input_data
        return None

    def get_expected(self, obj):
        """Retourne la sortie attendue du test_case associé."""
        if obj.test_case:
            return obj.test_case.expected_output
        return None


class SubmissionSerializer(serializers.ModelSerializer):
    test_results   = TestResultSerializer(many=True, read_only=True)
    username       = serializers.CharField(source='user.username',     read_only=True)
    exercise_title = serializers.CharField(source='exercise.title',    read_only=True)

    class Meta:
        model  = Submission
        fields = [
            'id',
            'user',
            'username',
            'exercise',
            'exercise_title',
            'code',
            'status',
            'submitted_at',
            'test_results',
        ]
        read_only_fields = ['id', 'submitted_at']


class SubmissionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Submission
        fields = ['exercise', 'code']

    def validate(self, data):
        exercise = data.get('exercise')
        if exercise and not exercise.is_published:
            raise serializers.ValidationError("Cet exercice n'est pas encore publié")
        return data
