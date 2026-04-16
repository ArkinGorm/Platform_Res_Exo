"""
CodeSandbox — exécution de code soumis par les étudiants.

Stratégie d'exécution (par ordre de priorité) :
  1. Docker  — si le socket /var/run/docker.sock est accessible (isolé, sécurisé)
  2. subprocess — fallback si Docker n'est pas disponible (serveur nu, CI, etc.)

Configurer via la variable d'environnement SANDBOX_BACKEND :
  SANDBOX_BACKEND=docker      → force Docker (lève une erreur si absent)
  SANDBOX_BACKEND=subprocess  → force subprocess
  SANDBOX_BACKEND=auto        → détecte automatiquement (défaut)
"""

import io
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
        'python':     [sys.executable],          # utilise le même Python que Django
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

    Usage identique à l'original :
        sandbox = CodeSandbox(language='python')
        results = sandbox.execute_with_tests(code, test_cases)
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

    def execute_with_tests(self, code, test_cases):
        results = []
        all_passed = True

        for test in test_cases:
            if self.language == 'javascript':
                test_script = f"""
{code}
try {{
    const input = {test.input_data};
    const args = Array.isArray(input) ? input : [input];
    const res = solution(...args);
    process.stdout.write(String(res));
    process.exit(0);
}} catch (e) {{
    process.stderr.write(String(e.message));
    process.exit(1);
}}
"""
            else:  # Python
                test_script = f"""
{code}
import sys
try:
    input_data = {test.input_data}
    args = input_data if isinstance(input_data, (list, tuple)) else [input_data]
    res = solution(*args)
    sys.stdout.write(str(res))
    sys.exit(0)
except Exception as e:
    sys.stderr.write(str(e))
    sys.exit(1)
"""

            start_time = time.time()
            output, error = self.execute(test_script)
            exec_time = (time.time() - start_time) * 1000

            expected = str(test.expected_output).strip()
            actual   = (output or '').strip()

            if actual == expected:
                passed = True
                error  = ''
            else:
                passed = False
                if not actual and not error:
                    error = 'No output returned'

            print(
                f"DEBUG: Input: {test.input_data} | "
                f"Obtenu: '{actual}' | "
                f"Attendu: '{expected}' | "
                f"Erreur: {error}"
            )

            results.append({
                'test_case_id': test.id,
                'passed': passed,
                'output': actual,
                'error': error,
                'execution_time': exec_time,
            })

            if not passed:
                all_passed = False

        return {'all_passed': all_passed, 'results': results}
