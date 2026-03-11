param($cmd)

switch ($cmd) {
    'build' { docker-compose build }
    'start' { docker-compose up -d }
    'stop' { docker-compose down }
    'restart'{ docker-compose restart }
    'logs' { docker-compose logs -f }
    'makemigrations' { docker-compose exec web python manage.py makemigrations }
    'install' {docker-compose exec web pip install -r requirements.txt}
    'migrate' { docker-compose exec web python manage.py migrate }
    'bash' { docker-compose exec web bash } # Permet d'ouvrir un terminal bash dans le conteneur web
    'shell' { docker-compose exec web python manage.py shell }
    'ps' { docker-compose ps }
    'createsuperuser' { docker-compose exec web python manage.py createsuperuser }
    default { Write-Host "Commandes: start, stop, logs, migrate, shell, ps" }
}
# Raccourci pour executer les commandes Docker et django dans mon environnement de développement