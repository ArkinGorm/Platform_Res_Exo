param($cmd, [string]$arg = "")

switch ($cmd) {
    # ── Docker ────────────────────────────────────────────────────────────────
    'build'       { docker-compose build }
    'start'       { docker-compose up -d }
    'stop'        { docker-compose down }
    'restart'     { docker-compose restart }
    'logs'        { docker-compose logs -f $arg }
    'ps'          { docker-compose ps }
    'bash'        { docker-compose exec web bash }
    'shell'       { docker-compose exec web python manage.py shell }
    'execute'     { docker-compose exec web python $arg }
    'install'     { docker-compose exec web pip install -r requirements.txt }
    'migrate'     { docker-compose exec web python manage.py migrate }
    'makemigrations' { docker-compose exec web python manage.py makemigrations }
    'createsuperuser' { docker-compose exec web python manage.py createsuperuser }
    'connexion'   { docker exec -it plateforme_Res_Exo psql -U olivier -d plateforme_Res_Exo_db }

    # ── Local (sans Docker) ───────────────────────────────────────────────────
    'runserver' {
        Set-Location backend
        python manage.py runserver
        Set-Location ..
    }
    'migrate-local' {
        Set-Location backend
        python manage.py migrate
        Set-Location ..
    }
    'makemigrations-local' {
        Set-Location backend
        if ($arg) { python manage.py makemigrations $arg }
        else       { python manage.py makemigrations }
        Set-Location ..
    }
    'shell-local' {
        Set-Location backend
        python manage.py shell
        Set-Location ..
    }
    'createsuperuser-local' {
        Set-Location backend
        python manage.py createsuperuser
        Set-Location ..
    }
    'celery-worker' {
        # Lance le worker Celery (nécessite Redis local sur le port 6379)
        Set-Location backend
        celery -A config worker --loglevel=info
        Set-Location ..
    }
    'check-ollama' {
        # Vérifie que Ollama est accessible et que qwen2.5-coder:7b est disponible
        Set-Location backend
        python -c "
import django, os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from exercises.Auto_Gen.providers import check_ollama_connection
import json
result = check_ollama_connection()
print(json.dumps(result, indent=2, ensure_ascii=False))
if result.get('reachable') and result.get('model_available'):
    print('[OK] Ollama operationnel.')
    sys.exit(0)
else:
    print('[ERREUR] Ollama NON accessible ou modele absent.')
    sys.exit(1)
"
        Set-Location ..
    }

    default {
        Write-Host ""
        Write-Host "=== Commandes Docker ==="
        Write-Host "  start, stop, restart, build, logs, ps, bash, shell"
        Write-Host "  migrate, makemigrations, createsuperuser, install, execute"
        Write-Host ""
        Write-Host "=== Commandes Locales (sans Docker) ==="
        Write-Host "  runserver          → python manage.py runserver"
        Write-Host "  migrate-local      → python manage.py migrate"
        Write-Host "  makemigrations-local [app] → python manage.py makemigrations"
        Write-Host "  shell-local        → python manage.py shell"
        Write-Host "  createsuperuser-local"
        Write-Host "  celery-worker      → celery -A config worker"
        Write-Host "  check-ollama       → verifie la connexion Ollama"
        Write-Host ""
    }
}
# Raccourci pour executer les commandes Docker et Django dans l'environnement de développement