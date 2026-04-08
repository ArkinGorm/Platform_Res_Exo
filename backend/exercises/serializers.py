from rest_framework import serializers
from .models import Exercise, TestCase


class TestCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model  = TestCase
        fields = ['id', 'input_data', 'expected_output', 'description', 'order']


class ExerciseSerializer(serializers.ModelSerializer):
    test_cases           = TestCaseSerializer(many=True, read_only=True)
    created_by_username  = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model  = Exercise
        fields = [
            'id', 'title', 'description', 'difficulty', 'language',
            'solution', 'created_by', 'created_by_username',
            'is_published', 'created_at', 'test_cases',
        ]
        read_only_fields = ['id', 'created_at', 'created_by']


class ExerciseListSerializer(serializers.ModelSerializer):
    """Version simplifiée pour la liste des exercices"""
    test_cases_count = serializers.IntegerField(source='test_cases.count', read_only=True)

    class Meta:
        model  = Exercise
        fields = ['id', 'title', 'difficulty', 'language', 'is_published',
                  'created_at', 'test_cases_count']


class ExerciseCreateSerializer(serializers.ModelSerializer):
    """Création d'un exercice avec ses test cases inline"""
    test_cases = TestCaseSerializer(many=True, required=False)

    class Meta:
        model  = Exercise
        fields = ['title', 'description', 'difficulty', 'language',
                  'solution', 'is_published', 'test_cases']

    def create(self, validated_data):
        test_cases_data = validated_data.pop('test_cases', [])
        exercise = Exercise.objects.create(**validated_data)
        for tc in test_cases_data:
            TestCase.objects.create(exercise=exercise, **tc)
        return exercise

    def update(self, instance, validated_data):
        test_cases_data = validated_data.pop('test_cases', None)

        # Mise à jour des champs de l'exercice
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Remplacement complet des test cases si fournis
        if test_cases_data is not None:
            instance.test_cases.all().delete()
            for tc in test_cases_data:
                TestCase.objects.create(exercise=instance, **tc)

        return instance
