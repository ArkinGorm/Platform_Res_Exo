from celery import shared_task
from .models import Submission, TestResult
from exercises.models import TestCase
from .sandbox import CodeSandbox
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=2) # On réduit un peu les retries pour les erreurs fatales
def execute_code_task(self, submission_id):
    submission = None  # Crucial pour éviter l'UnboundLocalError
    
    try:
        # 1. Récupération sécurisée de la soumission
        try:
            submission = Submission.objects.get(id=submission_id)
        except Submission.DoesNotExist:
            logger.error(f"OUPS !Submission {submission_id} introuvable.")
            return False

        # 2. Mise à jour initiale
        submission.status = 'processing' # On met 'processing' car 'pending' est le statut par défaut
        submission.save()
        
        # 3. Récupérer l'exercice et les tests
        exercise = submission.exercise
        test_cases = TestCase.objects.filter(exercise=exercise)
        
        # 4. Exécution Sandbox
        sandbox = CodeSandbox(language=exercise.language)
        results = sandbox.execute_with_tests(submission.code, test_cases)
        
        # 5. Sauvegarder les résultats (utilisation de TestResult)
        for result in results['results']:
            # Dans ton tasks.py, modifie la création du TestResult :
            TestResult.objects.create(
                submission=submission,
                test_case_id=result['test_case_id'],
                passed=result['passed'],
                actual_output=result.get('output') or "", # Force une chaîne vide si None
                error_message=result.get('error') or "",  # SOLUTION ICI : Force une chaîne vide si None
                execution_time=result.get('execution_time', 0)
            )
        
        # 6. Finalisation du statut
        submission.status = 'passed' if results['all_passed'] else 'failed'
        submission.execution_time = sum(r.get('execution_time', 0) for r in results['results'])
        submission.save()
        
        return {
            'submission_id': submission_id,
            'status': submission.status
        }
        
    except Exception as e:
        logger.error(f"Erreur Task {submission_id}: {str(e)}")
        
        # Si on a pu récupérer la soumission, on marque l'erreur en DB
        if submission:
            submission.status = 'error'
            submission.save()
        
        # On ne retry que si ce n'est pas une erreur de credentials (OperationalError)
        # Mais pour debug, on peut laisser le retry
        raise self.retry(exc=e, countdown=10)