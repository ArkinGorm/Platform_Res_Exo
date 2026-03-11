from rest_framework import serializers
from .models import Exercise, TestCase

class TestCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCase
        fields = ['id', 'input_data', 'expected_output', 'description', 'order']

class ExerciseSerializer(serializers.ModelSerializer):
    test_cases = TestCaseSerializer(many=True, read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = Exercise
        fields = ['id', 'title', 'description', 'difficulty', 'language', 
                  'solution', 'created_by', 'created_by_username', 
                  'is_published', 'created_at', 'test_cases']
        read_only_fields = ['id', 'created_at', 'created_by']

class ExerciseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = ['title', 'description', 'difficulty', 'language', 'solution', 'is_published']

class ExerciseListSerializer(serializers.ModelSerializer):
    """Version simplifiée pour la liste des exercices"""
    class Meta:
        model = Exercise
        fields = ['id', 'title', 'difficulty', 'language', 'created_at']