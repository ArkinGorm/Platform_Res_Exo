import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from exercises.models import Exercise, TestCase
from users.models import User

def create_test_exercises():
    # Récupérer un admin
    admin = User.objects.filter(role='admin').first()
    if not admin:
        admin = User.objects.create_superuser('admin', 'admin@test.com', 'admin123')
    
    # Exercice JavaScript : Somme
    ex1 = Exercise.objects.create(
        title="Addition simple",
        description="Écrire une fonction 'solution' qui prend deux nombres et retourne leur somme.",
        difficulty="facile",
        language="javascript",
        solution="function solution(a, b) { return a + b; }",
        created_by=admin,
        is_published=True
    )
    
    TestCase.objects.create(
        exercise=ex1,
        input_data="[2, 3]",
        expected_output="5",
        description="Addition d'entiers positifs",
        order=1
    )
    TestCase.objects.create(
        exercise=ex1,
        input_data="[-1, 1]",
        expected_output="0",
        description="Addition d'entiers avec un ou plusieurs négatifs",
        order=2
    )
    
    # Exercice Python : Maximum
    ex2 = Exercise.objects.create(
        title="Maximum de trois nombres",
        description="Écrire une fonction 'solution' qui retourne le plus grand de trois nombres.",
        difficulty="moyen",
        language="python",
        solution="def solution(a, b, c):\n    return max(a, b, c)",
        created_by=admin,
        is_published=True
    )
    
    TestCase.objects.create(
        exercise=ex2,
        input_data="[5, 2, 8]",
        expected_output="8",
        description="Maximum à la fin",
        order=1
    )
    TestCase.objects.create(
        exercise=ex2,
        input_data="[10, 10, 5]",
        expected_output="10",
        description="Égalité",
        order=2
    )
    
    print("✅ Exercices de test créés!")

if __name__ == "__main__":
    create_test_exercises()