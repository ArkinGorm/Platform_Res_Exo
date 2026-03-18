import docker
import time
import tarfile
import io


class CodeSandbox:
    def __init__(self, language='javascript'):
        self.client = docker.from_env()
        self.language = language

    def get_docker_config(self):
        configs = {
            'javascript': ('node:18-alpine', ['node', '/tmp/script.js']),
            'python': ('python:3.11-alpine', ['python3', '/tmp/script.py']),
        }
        return configs.get(self.language, ('python:3.11-alpine', ['python3', '/tmp/script.py']))

    def _make_tar(self, content: str, filename: str) -> io.BytesIO:
        """Crée une archive tar en mémoire contenant le script."""
        encoded = content.encode('utf-8')
        tarstream = io.BytesIO()
        with tarfile.open(fileobj=tarstream, mode='w') as tar:
            info = tarfile.TarInfo(name=filename)
            info.size = len(encoded)
            tar.addfile(info, io.BytesIO(encoded))
        tarstream.seek(0)
        return tarstream

    def execute(self, test_script: str, timeout: int = 10):
        image, command = self.get_docker_config()
        ext = 'script.js' if self.language == 'javascript' else 'script.py'
        container = None

        try:
            # 0. S'assurer que l'image est disponible localement
            try:
                self.client.images.get(image)
            except docker.errors.ImageNotFound:
                print(f"Image {image} introuvable, pull en cours...")
                self.client.images.pull(image)

            # 1. Créer le container SANS démarrer
            container = self.client.containers.create(
                image=image,
                command=command,
                network_disabled=True,
                mem_limit='128m',
                cpu_quota=50000,
            )

            # 2. Copier le script dans le container via put_archive
            tar_data = self._make_tar(test_script, ext)
            container.put_archive('/tmp', tar_data)

            # 3. Démarrer le container
            container.start()

            # 4. Attendre la fin avec timeout
            container.wait(timeout=timeout)

            # 5. Récupérer les logs séparément
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
            actual = (output or "").strip()

            if actual == expected:
                passed = True
                error = ""
            else:
                passed = False
                if not actual and not error:
                    error = "No output returned"

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
                'execution_time': exec_time
            })

            if not passed:
                all_passed = False

        return {'all_passed': all_passed, 'results': results}
