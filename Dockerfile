# Image de base python
From python:3.11-slim

# Variables d'environnement
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Définir le répertoire de travail
WORKDIR /app

# Installer les dépendances systèmes nécessaires
Run apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Installer les dépendances Pythonzzzz
COPY requirements.txt /app/
Run pip install --no-cache-dir -r requirements.txt

# Copier le projet
COPY . /app/

# Exposer le port de l'app
Expose 8000

# Commande par défaut
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
