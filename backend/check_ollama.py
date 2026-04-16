"""
Script de diagnostic Ollama.
Lance depuis le dossier backend/ :
    python check_ollama.py
"""
import os
import sys

# Charger les settings Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import django
django.setup()

import requests
from django.conf import settings

url = getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")
model = getattr(settings, "OLLAMA_MODEL", "qwen2.5-coder:7b")

print(f"\n{'='*50}")
print(f"  Diagnostic Ollama")
print(f"{'='*50}")
print(f"  URL configurée  : {url}")
print(f"  Modèle configuré: {model}")
print(f"  EXECUTION_MODE  : {getattr(settings, 'EXECUTION_MODE', 'local')}")
print(f"{'='*50}\n")

try:
    r = requests.get(f"{url}/api/tags", timeout=5)
    print(f"✅ Ollama est accessible (HTTP {r.status_code})")
    models = [m["name"] for m in r.json().get("models", [])]
    print(f"   Modèles disponibles : {models or '(aucun)'}")
    if any(model in m for m in models):
        print(f"✅ Le modèle '{model}' est bien présent !")
    else:
        print(f"❌ Le modèle '{model}' est ABSENT.")
        print(f"   → Lance : ollama pull {model}")
except requests.exceptions.ConnectionError:
    print(f"❌ Impossible de joindre Ollama à {url}")
    print(f"   → Vérifie qu'Ollama est bien lancé : ollama serve")
    print(f"   → Et que l'URL dans .env est correcte (OLLAMA_BASE_URL)")
except Exception as e:
    print(f"❌ Erreur : {e}")

print()
