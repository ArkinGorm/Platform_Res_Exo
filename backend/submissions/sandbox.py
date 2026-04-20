"""
CodeSandbox — exécution de code soumis par les étudiants.

Stratégie d'exécution (par ordre de priorité) :
  1. Docker  — si le socket /var/run/docker.sock est accessible (isolé, sécurisé)
  2. subprocess — fallback si Docker n'est pas disponible (serveur nu, CI, etc.)

Configurer via la variable d'environnement SANDBOX_BACKEND :
  SANDBOX_BACKEND=docker      → force Docker (lève une erreur si absent)
  SANDBOX_BACKEND=subprocess  → force subprocess
  SANDBOX_BACKEND=auto        → détecte automatiquement (défaut)

Types d'exercices supportés :
  - "function"    : solution(*args) → valeur  [défaut]
  - "simulation"  : séquence de commandes [[cmd, args...], ...]  ex: LRUCache
  - "stdout"      : solution(*args) écrit sur stdout, pas de return
"""

import io
import json
import os
import sys
import time
import tarfile
import tempfile
import subprocess

# ── Détection du backend ──────────────────────────────────────────────────────

def _docker_available() -> bool:
    """Vérifie que le socket Docker est accessible."""
    try:
        import docker
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


_BACKEND_ENV = os.environ.get('SANDBOX_BACKEND', 'auto').lower()

if _BACKEND_ENV == 'docker':
    USE_DOCKER = True
elif _BACKEND_ENV == 'subprocess':
    USE_DOCKER = False
else:
    USE_DOCKER = _docker_available()


# ── Détection du type d'exercice ─────────────────────────────────────────────

def _detect_exercise_type(input_data: str) -> str:
    """
    Détecte le type d'exercice à partir de l'input_data du premier test case.

    Retourne :
      "simulation" → input est une liste de listes [[cmd, args...], ...]
                     ex: [["LRUCache", 2], ["put", 1, 1], ["get", 1]]
      "function"   → tout le reste (défaut)
    """
    stripped = input_data.strip()
    if stripped.startswith("[["):                   # if stripped.startswith("[["):
        try:
            parsed = json.loads(stripped)
            if (
                isinstance(parsed, list)
                and len(parsed) > 0
                and isinstance(parsed[0], list)
                and len(parsed[0]) > 0
                and isinstance(parsed[0][0], str)
            ):
                return "simulation"
        except (json.JSONDecodeError, ValueError):
            pass
    return "function"


# ── Générateurs de scripts de test ───────────────────────────────────────────

def _make_function_script(language: str, code: str, input_data: str) -> str:
    """
    Script standard : appelle solution(*args) et imprime le résultat.
    """
    if language == 'javascript':
        return f"""\
{code}
try {{
    const input = {input_data};
    const args = Array.isArray(input) ? input : (input !== undefined ? [input] : []);
    const res = solution(...args);
    if (res !== undefined) process.stdout.write(String(res));
    process.exit(0);
}} catch (e) {{
    process.stderr.write(String(e.message));
    process.exit(1);
}}
"""
    else:  # python
        return f"""\
{code}
import sys, json
try:
    input_data = {input_data}
    if input_data is None:
        args = []
    elif isinstance(input_data, (list, tuple)):
        args = list(input_data)
    else:
        args = [input_data]
    res = solution(*args)
    if res is not None:
        sys.stdout.write(str(res))
    sys.exit(0)
except Exception as e:
    sys.stderr.write(str(e))
    sys.exit(1)
"""


def _make_simulation_script(language: str, code: str, input_data: str, expected_output: str) -> str:
    """
    Script pour les exercices de type simulation (ex: LRUCache, MinStack…).

    L'input est une liste de listes : [[ClassName, ctor_arg], [method, args…], ...]
    L'output attendu est une liste de résultats  : [null, null, 1, ...]

    Le script :
      1. Instancie la classe avec les args du premier élément
      2. Appelle chaque méthode suivante
      3. Collecte les résultats en tenant compte de None/null
      4. Compare avec expected (JSON) et affiche "PASS" ou le résultat réel
    """
    if language == 'python':
        return f"""\
{code}
import sys, json

commands = {input_data}
class_name = commands[0][0]
ctor_args  = commands[0][1:]

cls = globals().get(class_name)
if cls is None:
    sys.stderr.write(f"Classe {{class_name}} introuvable dans le code fourni")
    sys.exit(1)

obj = cls(*ctor_args)
results = [None]  # premier élément = constructeur

for cmd in commands[1:]:
    method_name = cmd[0]
    args        = cmd[1:]
    method = getattr(obj, method_name, None)
    if method is None:
        sys.stderr.write(f"Méthode {{method_name}} introuvable")
        sys.exit(1)
    ret = method(*args)
    results.append(ret)

# Normalise None → null pour la comparaison
def normalize(v):
    if v is None:
        return None
    return v

normalized = [normalize(r) for r in results]
sys.stdout.write(json.dumps(normalized))
sys.exit(0)
"""
    else:  # javascript
        return f"""\
{code}
try {{
    const commands = {input_data};
    const className = commands[0][0];
    const ctorArgs  = commands[0].slice(1);

    const cls = eval(className);
    if (typeof cls === 'undefined') throw new Error(`Classe ${{className}} introuvable`);
    const obj = new cls(...ctorArgs);
    const results = [null];

    for (let i = 1; i < commands.length; i++) {{
        const [methodName, ...args] = commands[i];
        if (typeof obj[methodName] !== 'function') throw new Error(`Méthode ${{methodName}} introuvable`);
        const ret = obj[methodName](...args);
        results.push(ret === undefined ? null : ret);
    }}

    process.stdout.write(JSON.stringify(results));
    process.exit(0);
}} catch (e) {{
    process.stderr.write(String(e.message));
    process.exit(1);
}}
"""


def _compare_simulation_output(actual_str: str, expected_str: str) -> bool:
    """
    Compare deux sorties JSON de simulation de manière souple.
    Gère None/null, -1, entiers, etc.
    """
    try:
        actual   = json.loads(actual_str)
        expected = json.loads(expected_str)

        def norm(v):
            if v is None:
                return None
            if isinstance(v, float) and v == int(v):
                return int(v)
            return v

        actual_n   = [norm(x) for x in actual]
        expected_n = [norm(x) for x in expected]
        return actual_n == expected_n
    except Exception:
        return str(actual_str).strip() == str(expected_str).strip()


# ══════════════════════════════════════════════════════════════════════════════
#  Backend Docker
# ══════════════════════════════════════════════════════════════════════════════

class _DockerSandbox:
    """Exécution isolée via Docker (comportement d'origine)."""

    def __init__(self, language='javascript'):
        import docker as _docker
        self.client = _docker.from_env()
        self.language = language

    def get_docker_config(self):
        configs = {
            'javascript': ('node:18-alpine', ['node', '/tmp/script.js']),
            'python':     ('python:3.11-alpine', ['python3', '/tmp/script.py']),
        }
        return configs.get(self.language, ('python:3.11-alpine', ['python3', '/tmp/script.py']))

    def _make_tar(self, content: str, filename: str) -> io.BytesIO:
        encoded = content.encode('utf-8')
        tarstream = io.BytesIO()
        with tarfile.open(fileobj=tarstream, mode='w') as tar:
            info = tarfile.TarInfo(name=filename)
            info.size = len(encoded)
            tar.addfile(info, io.BytesIO(encoded))
        tarstream.seek(0)
        return tarstream

    def execute(self, test_script: str, timeout: int = 10):
        import docker
        image, command = self.get_docker_config()
        ext = 'script.js' if self.language == 'javascript' else 'script.py'
        container = None
        try:
            try:
                self.client.images.get(image)
            except docker.errors.ImageNotFound:
                print(f"Image {image} introuvable, pull en cours…")
                self.client.images.pull(image)

            container = self.client.containers.create(
                image=image,
                command=command,
                network_disabled=True,
                mem_limit='128m',
                cpu_quota=50000,
            )
            tar_data = self._make_tar(test_script, ext)
            container.put_archive('/tmp', tar_data)
            container.start()
            container.wait(timeout=timeout)

            output = container.logs(stdout=True, stderr=False).decode('utf-8').strip()
            error  = container.logs(stdout=False, stderr=True).decode('utf-8').strip()
            return output, error

        except Exception as e:
            return None, str(e)
        finally:
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass


# ══════════════════════════════════════════════════════════════════════════════
#  Backend subprocess (sans Docker)
# ══════════════════════════════════════════════════════════════════════════════

class _SubprocessSandbox:
    """
    Exécution via subprocess — moins isolé que Docker mais fonctionnel
    sur tout serveur disposant de Python 3 / Node.js.

    ⚠️  Ne pas utiliser en production exposée : le code student tourne dans
        le même processus OS que Django. Acceptable pour un intranet ou un
        environnement de dev/test.
    """

    INTERPRETERS = {
        'python':     [sys.executable],
        'javascript': ['node'],
        'java':       ['java'],
    }

    def __init__(self, language='javascript'):
        self.language = language

    def _get_suffix(self):
        return {'python': '.py', 'javascript': '.js', 'java': '.java'}.get(self.language, '.py')

    def execute(self, test_script: str, timeout: int = 10):
        interpreter = self.INTERPRETERS.get(self.language)
        if not interpreter:
            return None, f"Langage non supporté : {self.language}"

        suffix = self._get_suffix()
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix=suffix,
                                             delete=False, encoding='utf-8') as f:
                f.write(test_script)
                tmp_path = f.name

            result = subprocess.run(
                interpreter + [tmp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.stdout.strip(), result.stderr.strip()

        except subprocess.TimeoutExpired:
            return None, f"Timeout dépassé ({timeout}s)"
        except FileNotFoundError:
            return None, (
                f"Interpréteur introuvable : {interpreter[0]}. "
                "Assurez-vous que Node.js / Python est installé et dans le PATH."
            )
        except Exception as e:
            return None, str(e)
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass


# ══════════════════════════════════════════════════════════════════════════════
#  Classe publique : CodeSandbox
# ══════════════════════════════════════════════════════════════════════════════

class CodeSandbox:
    """
    Interface unifiée — choisit automatiquement Docker ou subprocess.

    Supporte trois types d'exercices :
      - "function"   : solution(*args) → valeur (défaut)
      - "simulation" : séquence de commandes [[Class, args], [method, args], ...]
      - "stdout"     : solution() écrit sur stdout (print/console.log)
    """

    def __init__(self, language='javascript'):
        self.language = language
        if USE_DOCKER:
            self._backend = _DockerSandbox(language)
        else:
            self._backend = _SubprocessSandbox(language)
        print(f"[Sandbox] backend={('docker' if USE_DOCKER else 'subprocess')}, lang={language}")

    def execute(self, test_script: str, timeout: int = 10):
        return self._backend.execute(test_script, timeout)

    def execute_with_tests(self, code: str, test_cases):
        """
        Exécute le code contre tous les test cases.

        Détecte automatiquement le type d'exercice à partir du premier test case
        (simulation vs function) et génère le script adapté.
        """
        results = []
        all_passed = True

        # Déterminer le type d'exercice à partir du premier test case
        first_input = str(test_cases[0].input_data) if test_cases else ""
        exercise_type = _detect_exercise_type(first_input)

        print(f"[Sandbox] exercise_type={exercise_type}, tests={len(list(test_cases))}")

        for test in test_cases:
            input_str = str(test.input_data)
            expected  = str(test.expected_output).strip()

            # Générer le script adapté au type d'exercice
            if exercise_type == "simulation":
                test_script = _make_simulation_script(
                    self.language, code, input_str, expected
                )
            else:
                test_script = _make_function_script(self.language, code, input_str)

            start_time = time.time()
            output, error = self.execute(test_script)
            exec_time = (time.time() - start_time) * 1000

            actual = (output or '').strip()

            # Comparaison adaptée au type
            if exercise_type == "simulation":
                passed = _compare_simulation_output(actual, expected) if not error else False
            else:
                passed = (actual == expected) if not error else False

            if not passed and not actual and not error:
                error = 'No output returned'

            print(
                f"DEBUG [{exercise_type}]: Input: {input_str[:60]} | "
                f"Obtenu: '{actual[:60]}' | "
                f"Attendu: '{expected[:60]}' | "
                f"Erreur: {error[:80] if error else ''}"
            )

            results.append({
                'test_case_id':   test.id,
                'passed':         passed,
                'output':         actual,
                'error':          error,
                'execution_time': exec_time,
            })

            if not passed:
                all_passed = False

        return {'all_passed': all_passed, 'results': results}
