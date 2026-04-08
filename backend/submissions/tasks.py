from celery import shared_task
from .models import Submission, TestResult
from exercises.models import TestCase
from .sandbox import CodeSandbox
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2)
def execute_code_task(self, submission_id):
    submission = None

    try:
        # 1. Récupération sécurisée de la soumission
        try:
            submission = Submission.objects.get(id=submission_id)
        except Submission.DoesNotExist:
            logger.error(f"Submission {submission_id} introuvable.")
            return False

        # 2. Garder le statut 'pending' pendant l'exécution
        #    (évite d'écrire 'processing' qui n'est pas dans STATUS_CHOICES)
        submission.status = 'pending'
        submission.save()

        # 3. Récupérer l'exercice et les tests
        exercise = submission.exercise
        test_cases = TestCase.objects.filter(exercise=exercise).order_by('order')

        # 4. Exécution Sandbox
        sandbox = CodeSandbox(language=exercise.language)
        results = sandbox.execute_with_tests(submission.code, test_cases)

        # 5. Supprimer les anciens TestResult avant de sauvegarder
        #    (protection contre les doublons en cas de retry Celery)
        TestResult.objects.filter(submission=submission).delete()

        # 6. Sauvegarder les résultats
        for result in results['results']:
            TestResult.objects.create(
                submission=submission,
                test_case_id=result['test_case_id'],
                passed=result['passed'],
                actual_output=result.get('output') or "",
                error_message=result.get('error') or "",
                execution_time=result.get('execution_time', 0),
            )

        # 7. Finalisation du statut
        submission.status = 'passed' if results['all_passed'] else 'failed'
        submission.save()

        return {
            'submission_id': submission_id,
            'status': submission.status,
        }

    except Exception as e:
        logger.error(f"Erreur Task {submission_id}: {str(e)}")

        if submission:
            submission.status = 'failed'
            submission.save()

        raise self.retry(exc=e, countdown=10)
