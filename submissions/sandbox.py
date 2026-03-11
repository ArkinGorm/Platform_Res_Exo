# Gestion du conteneur docker
import docker
import tempfile
import os
import time
from pathlib import Path

class CodeSandbox:
    """
    Exécute du code dans un conteneur Docker isolé
    """
    
    def __init__(self, language='javascript'):
        self.client = docker.from_env()
        self.language = language
        
    def get_docker_image(self):
        """Retourne l'image Docker selon le langage"""
        images = {
            'javascript': 'node:18-slim',
            'python': 'python:3.11-slim',
            'java': 'openjdk:17-slim',
        }
        return images.get(self.language, 'python:3.11-slim')
    
    def get_command(self, code_file):
        """Retourne la commande d'exécution selon le langage"""
        commands = {
            'javascript': f'node {code_file}',
            'python': f'python {code_file}',
            'java': f'java {code_file}',
        }
        return commands.get(self.language, f'python {code_file}')
    
    def create_code_file(self, code):
        """Crée un fichier temporaire avec le code"""
        extensions = {
            'javascript': '.js',
            'python': '.py',
            'java': '.java',
        }
        ext = extensions.get(self.language, '.txt')
        
        with tempfile.NamedTemporaryFile(mode='w', suffix=ext, delete=False) as f:
            f.write(code)
            return f.name
    
    def execute(self, code, timeout=5):
        """
        Exécute le code dans un conteneur Docker
        Retourne: (output, error, execution_time)
        """
        code_file = None
        try:
            # Créer le fichier de code
            code_file = self.create_code_file(code)
            file_name = os.path.basename(code_file)
            file_dir = os.path.dirname(code_file)
            
            # Commande à exécuter
            cmd = self.get_command(file_name)
            
            start_time = time.time()
            
            # Exécuter dans Docker
            container = self.client.containers.run(
                image=self.get_docker_image(),
                command=cmd,
                volumes={file_dir: {'bind': '/workspace', 'mode': 'ro'}},
                working_dir='/workspace',
                mem_limit='256m',
                cpu_quota=50000,  # 0.5 CPU
                network_disabled=True,  # Pas d'accès réseau
                read_only=True,  # Système de fichiers en lecture seule
                remove=True,
                detach=True
            )
            
            # Attendre le résultat avec timeout
            try:
                result = container.wait(timeout=timeout)
                logs = container.logs(stdout=True, stderr=True).decode('utf-8')
                execution_time = (time.time() - start_time) * 1000  # en ms
                
                return logs, None, execution_time
                
            except Exception as e:
                container.kill()
                return None, f"Timeout après {timeout} secondes", (time.time() - start_time) * 1000
                
        except Exception as e:
            return None, str(e), 0
            
        finally:
            # Nettoyer le fichier temporaire
            if code_file and os.path.exists(code_file):
                os.unlink(code_file)
    
    def execute_with_tests(self, code, test_cases):
        """
        Exécute le code avec des cas de test
        """
        results = []
        all_passed = True
        
        for test in test_cases:
            # Pour les tests, on injecte l'input dans le code
            if self.language == 'javascript':
                test_code = f"""
                const input = {test.input_data};
                {code}
                console.log(solution(...(Array.isArray(input) ? input : [input])));
                """
            elif self.language == 'python':
                test_code = f"""
import sys
from io import StringIO

input_data = {test.input_data}
{code}

# Capturer la sortie
old_stdout = sys.stdout
sys.stdout = StringIO()

try:
    if isinstance(input_data, (list, tuple)):
        result = solution(*input_data)
    else:
        result = solution(input_data)
    print(result)
finally:
    sys.stdout = old_stdout
"""
            else:
                test_code = code
            
            output, error, exec_time = self.execute(test_code)
            
            passed = False
            if output and not error:
                # Comparer la sortie avec l'attendu
                passed = output.strip() == str(test.expected_output).strip()
            
            results.append({
                'test_case_id': test.id,
                'input': test.input_data,
                'expected': test.expected_output,
                'output': output.strip() if output else None,
                'error': error,
                'passed': passed,
                'execution_time': exec_time
            })
            
            if not passed:
                all_passed = False
        
        return {
            'all_passed': all_passed,
            'results': results,
            'total_tests': len(test_cases),
            'passed_tests': sum(1 for r in results if r['passed'])
        }