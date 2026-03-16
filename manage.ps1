param($cmd)

switch ($cmd) {
    'build' { docker-compose build }
    'start' { docker-compose up -d }
    'stop' { docker-compose down }
    'execute' { docker-compose exec web python $args } 
    'restart'{ docker-compose restart }
    'logs' { docker-compose logs -f $args }
    'makemigrations' { docker-compose exec web python manage.py makemigrations }
    'install' {docker-compose exec web pip install -r requirements.txt}
    'migrate' { docker-compose exec web python manage.py migrate }
    'bash' { docker-compose exec web bash } # Permet d'ouvrir un terminal bash dans le conteneur web
    'shell' { docker-compose exec web python manage.py shell }
    'ps' { docker-compose ps }
    'createsuperuser' { docker-compose exec web python manage.py createsuperuser }
    'connexion' { docker exec -it plateforme_Res_Exo psql -U olivier -d plateforme_Res_Exo_db }
    default { Write-Host "Commandes: start, stop, logs, migrate, shell, ps, makemigrations, migrate, restart, install, execute" }
}
# Raccourci pour executer les commandes Docker et django dans mon environnement de développement