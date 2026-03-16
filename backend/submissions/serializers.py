from rest_framework import serializers
from .models import Submission, TestResult
from exercises.models import Exercise

class TestResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestResult
        fields = ['id', 'test_case', 'passed', 'actual_output', 'error_message']

class SubmissionSerializer(serializers.ModelSerializer):
    test_results = TestResultSerializer(many=True, read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    exercise_title = serializers.CharField(source='exercise.title', read_only=True)

    class Meta:
        model = Submission
        fields = ['id', 'user', 'username', 'exercise', 'exercise_title', 
                  'code', 'status', 'submitted_at', 'test_results']
        read_only_fields = ['id', 'submitted_at']

class SubmissionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = ['exercise', 'code']

    def validate(self, data):
        # Vérifier que l'exercice existe et est publié
        exercise = data.get('exercise')
        if exercise and not exercise.is_published:
            raise serializers.ValidationError("Cet exercice n'est pas encore publié")
        return data