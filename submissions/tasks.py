from celery import shared_task
from .models import Submission, TestResult
from exercises.models import TestCase
from .sandbox import CodeSandbox
import json

@shared_task(bind=True, max_retries=3)
def execute_code_task(self, submission_id):
    """
    Tâche Celery pour exécuter le code en arrière-plan
    """
    try:
        # Récupérer la soumission
        submission = Submission.objects.get(id=submission_id)
        submission.status = 'pending'
        submission.save()
        
        # Récupérer l'exercice et les tests
        exercise = submission.exercise
        test_cases = TestCase.objects.filter(exercise=exercise)
        
        # Créer le sandbox
        sandbox = CodeSandbox(language=exercise.language)
        
        # Exécuter les tests
        results = sandbox.execute_with_tests(submission.code, test_cases)
        
        # Sauvegarder les résultats
        for result in results['results']:
            TestResult.objects.create(
                submission=submission,
                test_case_id=result['test_case_id'],
                passed=result['passed'],
                actual_output=result['output'] or result['error'],
                error_message=result['error'],
                execution_time=result['execution_time']
            )
        
        # Mettre à jour le statut de la soumission
        submission.status = 'passed' if results['all_passed'] else 'failed'
        submission.execution_time = sum(r['execution_time'] for r in results['results'])
        submission.save()
        
        return {
            'submission_id': submission_id,
            'status': submission.status,
            'results': results
        }
        
    except Exception as e:
        # En cas d'erreur, réessayer
        submission.status = 'error'
        submission.save()
        self.retry(exc=e, countdown=60)