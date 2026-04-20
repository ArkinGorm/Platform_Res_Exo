from celery import shared_task
from .models import Submission, TestResult
from exercises.models import TestCase
from .sandbox import CodeSandbox
import logging

logger = logging.getLogger(__name__)


def _run_submission(submission_id: int) -> dict:
    """
    Logique d'exécution pure — appelable directement (mode local) ou
    depuis la tâche Celery (mode celery).
    """
    submission = None
    try:
        try:
            submission = Submission.objects.get(id=submission_id)
        except Submission.DoesNotExist:
            logger.error("Submission %d introuvable.", submission_id)
            return {"success": False}

        submission.status = 'pending'
        submission.save()

        exercise = submission.exercise
        test_cases = TestCase.objects.filter(exercise=exercise).order_by('order')

        sandbox = CodeSandbox(language=exercise.language)
        results = sandbox.execute_with_tests(submission.code, test_cases)

        # Protection contre les doublons en cas de retry
        TestResult.objects.filter(submission=submission).delete()

        for result in results['results']:
            TestResult.objects.create(
                submission=submission,
                test_case_id=result['test_case_id'],
                passed=result['passed'],
                actual_output=result.get('output') or '',
                error_message=result.get('error') or '',
                execution_time=result.get('execution_time', 0),
            )

        submission.status = 'passed' if results['all_passed'] else 'failed'
        submission.save()

        return {
            'submission_id': submission_id,
            'status': submission.status,
        }

    except Exception as e:
        logger.error("Erreur _run_submission %d : %s", submission_id, e)
        if submission:
            submission.status = 'failed'
            submission.save()
        raise


@shared_task(bind=True, max_retries=2)
def execute_code_task(self, submission_id):
    try:
        return _run_submission(submission_id)
    except Exception as e:
        raise self.retry(exc=e, countdown=10)
