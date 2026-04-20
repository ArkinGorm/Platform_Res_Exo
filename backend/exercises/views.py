from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import Exercise, TestCase
from .serializers import (
    ExerciseSerializer, ExerciseCreateSerializer,
    ExerciseListSerializer, TestCaseSerializer,
)
from users.permissions import IsAdmin
from submissions.sandbox import CodeSandbox
import logging

logger = logging.getLogger(__name__)


class ExerciseViewSet(viewsets.ModelViewSet):
    queryset = Exercise.objects.all()
    filter_backends   = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields  = ['difficulty', 'language', 'is_published']
    search_fields     = ['title', 'description']
    ordering_fields   = ['created_at', 'title']

    def get_serializer_class(self):
        if self.action == 'list':
            return ExerciseListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ExerciseCreateSerializer
        return ExerciseSerializer

    def get_permissions(self):
        public_actions = ['published']
        admin_actions  = [
            'create', 'update', 'partial_update', 'destroy',
            'publish', 'unpublish', 'test_exercise', 'validate_tests',
            'test_cases', 'delete_test_case', 'unpublished',
        ]
        if self.action in admin_actions:
            return [IsAdmin()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    # ── Exercices publiés ───────────────────────────────────────
    @action(detail=False, methods=['get'])
    def published(self, request):
        exercises = self.get_queryset().filter(is_published=True)
        serializer = ExerciseListSerializer(exercises, many=True)
        return Response(serializer.data)

    # ── Exercices non publiés ───────────────────────────────────
    @action(detail=False, methods=['get'], permission_classes=[IsAdmin])
    def unpublished(self, request):
        exercises = self.get_queryset().filter(is_published=False)
        serializer = ExerciseListSerializer(exercises, many=True)
        return Response(serializer.data)

    # ── Publier ─────────────────────────────────────────────────
    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def publish(self, request, pk=None):
        exercise = self.get_object()
        if not exercise.test_cases.exists():
            return Response(
                {'error': 'Impossible de publier sans test cases'},
                status=status.HTTP_400_BAD_REQUEST
            )
        exercise.is_published = True
        exercise.save()
        return Response({'status': 'Exercice publié', 'is_published': True})

    # ── Dépublier ───────────────────────────────────────────────
    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def unpublish(self, request, pk=None):
        exercise = self.get_object()
        exercise.is_published = False
        exercise.save()
        return Response({'status': 'Exercice dépublié', 'is_published': False})

    # ── CRUD test cases ─────────────────────────────────────────
    @action(detail=True, methods=['get', 'post'], permission_classes=[IsAdmin])
    def test_cases(self, request, pk=None):
        exercise = self.get_object()
        if request.method == 'GET':
            serializer = TestCaseSerializer(
                exercise.test_cases.all().order_by('order'), many=True
            )
            return Response(serializer.data)
        serializer = TestCaseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(exercise=exercise)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'],
            url_path='test_cases/(?P<tc_id>[^/.]+)',
            permission_classes=[IsAdmin])
    def delete_test_case(self, request, pk=None, tc_id=None):
        exercise = self.get_object()
        try:
            exercise.test_cases.get(id=tc_id).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except TestCase.DoesNotExist:
            return Response({'error': 'Test case introuvable'}, status=status.HTTP_404_NOT_FOUND)

    # ── Tester la solution de référence ─────────────────────────
    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def test_exercise(self, request, pk=None):
        exercise  = self.get_object()
        code      = request.data.get('code', exercise.solution)
        if not code:
            return Response({'error': 'Aucun code fourni'}, status=status.HTTP_400_BAD_REQUEST)
        test_cases = exercise.test_cases.all().order_by('order')
        if not test_cases.exists():
            return Response({'error': 'Aucun test case défini'}, status=status.HTTP_400_BAD_REQUEST)
        sandbox = CodeSandbox(language=exercise.language)
        results = sandbox.execute_with_tests(code, test_cases)
        return Response({
            'all_passed': results['all_passed'],
            'results':    results['results'],
            'total':      len(results['results']),
            'passed':     sum(1 for r in results['results'] if r['passed']),
        })

    # ── Validation & optimisation des test cases ────────────────
    @action(detail=False, methods=['post'], permission_classes=[IsAdmin])
    def validate_tests(self, request):
        """
        Analyse complète des test cases AVANT sauvegarde.
        Body : { language, solution, test_cases: [...] }
        Retourne un rapport détaillé avec :
          - cohérence des expected_output (calculé vs saisi)
          - doublons
          - tests "passoires" (code trivial qui passe quand même)
          - clarté de l'énoncé
        """
        language   = request.data.get('language', 'python')
        solution   = request.data.get('solution', '').strip()
        test_cases = request.data.get('test_cases', [])
        description = request.data.get('description', '').strip()
        title       = request.data.get('title', '').strip()

        report = {
            'issues':    [],   # problèmes bloquants
            'warnings':  [],   # avertissements non bloquants
            'auto_fixed': [],  # corrections auto appliquées
            'test_cases': [],  # test cases avec statut individuel
            'can_publish': True,
        }

        if not test_cases:
            report['issues'].append('Aucun test case défini.')
            report['can_publish'] = False
            return Response(report)

        # ── 1. Vérification clarté de l'énoncé ─────────────────
        clarity_issues = _check_description_clarity(title, description, language)
        report['warnings'].extend(clarity_issues)

        # ── 2. Détection des doublons ───────────────────────────
        seen_inputs = {}
        for i, tc in enumerate(test_cases):
            inp = str(tc.get('input_data', '')).strip()
            if inp in seen_inputs:
                report['issues'].append(
                    f'Test {i+1} et Test {seen_inputs[inp]+1} ont la même entrée : "{inp}"'
                )
                report['can_publish'] = False
            else:
                seen_inputs[inp] = i

        # ── 3. Vérification inputs/outputs non vides ────────────
        for i, tc in enumerate(test_cases):
            if not str(tc.get('input_data', '')).strip():
                report['issues'].append(f'Test {i+1} : input_data vide')
                report['can_publish'] = False
            if not str(tc.get('expected_output', '')).strip():
                report['issues'].append(f'Test {i+1} : expected_output vide')
                report['can_publish'] = False

        # ── 4. Auto-calcul & cohérence des expected_output ──────
        if solution:
            sandbox = CodeSandbox(language=language)

            class _FakeTc:
                def __init__(self, data, idx):
                    self.id              = idx
                    self.input_data      = data.get('input_data', '')
                    self.expected_output = data.get('expected_output', '')

            fake_tcs = [_FakeTc(tc, i) for i, tc in enumerate(test_cases)]
            run_results = sandbox.execute_with_tests(solution, fake_tcs)

            updated_tcs = []
            for i, (tc, run) in enumerate(zip(test_cases, run_results['results'])):
                tc_report = {
                    'index':          i,
                    'input_data':     tc.get('input_data', ''),
                    'expected_output': tc.get('expected_output', ''),
                    'computed_output': run.get('output', ''),
                    'status':         'ok',
                    'messages':       [],
                }

                computed = str(run.get('output', '')).strip()
                stated   = str(tc.get('expected_output', '')).strip()
                error    = run.get('error', '')

                if error:
                    tc_report['status'] = 'error'
                    tc_report['messages'].append(f'Erreur d\'exécution : {error}')
                    report['issues'].append(f'Test {i+1} : la solution plante sur cet input ({error})')
                    report['can_publish'] = False
                elif computed != stated:
                    tc_report['status'] = 'mismatch'
                    tc_report['messages'].append(
                        f'expected_output "{stated}" ≠ résultat calculé "{computed}"'
                    )
                    # Auto-fix : propose la valeur calculée
                    tc_report['suggested_output'] = computed
                    report['auto_fixed'].append(
                        f'Test {i+1} : expected_output corrigé de "{stated}" → "{computed}"'
                    )
                    tc['expected_output'] = computed  # correction auto

                updated_tcs.append(tc_report)

            report['test_cases'] = updated_tcs

            # ── 5. Détection tests "passoires" ──────────────────
            # On teste avec un code trivial qui retourne toujours None/undefined
            trivial_code = (
                'def solution(*args):\n    return None'
                if language == 'python'
                else 'function solution(...args) { return undefined; }'
            )
            trivial_results = sandbox.execute_with_tests(trivial_code, fake_tcs)
            passoire_count  = sum(1 for r in trivial_results['results'] if r['passed'])
            if passoire_count > 0:
                report['warnings'].append(
                    f'{passoire_count} test(s) passent avec un code vide/trivial — '
                    f'vérifie que les expected_output ne sont pas "None" ou vides.'
                )

        else:
            report['warnings'].append(
                'Aucune solution de référence — impossible de vérifier la cohérence des expected_output.'
            )
            report['test_cases'] = [
                {'index': i, 'input_data': tc.get('input_data'), 
                 'expected_output': tc.get('expected_output'), 'status': 'unchecked'}
                for i, tc in enumerate(test_cases)
            ]

        # Résumé final
        if not report['issues']:
            report['can_publish'] = True

        return Response(report)


# ── Helpers ─────────────────────────────────────────────────────

def _check_description_clarity(title, description, language):
    """Vérifie que l'énoncé est suffisamment clair."""
    warnings = []

    if len(title.strip()) < 5:
        warnings.append('Le titre est trop court — sois plus descriptif.')

    if len(description.strip()) < 30:
        warnings.append('L\'énoncé est très court — explique clairement ce que la fonction doit faire.')

    keywords_what = ['retourne', 'retourner', 'renvoie', 'renvoyer', 'return',
                     'calcule', 'calculer', 'affiche', 'trouve', 'trouver', 'donne']
    keywords_input = ['prend', 'reçoit', 'paramètre', 'argument', 'entrée', 'input', 'takes']

    desc_lower = description.lower()

    if not any(k in desc_lower for k in keywords_what):
        warnings.append(
            'L\'énoncé ne précise pas clairement ce que la fonction doit retourner. '
            'Ajoute une phrase comme "La fonction doit retourner..."'
        )

    if not any(k in desc_lower for k in keywords_input):
        warnings.append(
            'L\'énoncé ne décrit pas les paramètres d\'entrée. '
            'Précise ce que la fonction reçoit en argument.'
        )

    lang_label = 'JavaScript' if language == 'javascript' else 'Python'
    if lang_label.lower() not in desc_lower and 'solution' not in desc_lower:
        warnings.append(
            f'Pense à mentionner que la fonction s\'appelle "solution" '
            f'et qu\'elle est écrite en {lang_label}.'
        )

    return warnings
