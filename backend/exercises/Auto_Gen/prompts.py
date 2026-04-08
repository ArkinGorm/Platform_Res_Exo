"""
LangChain prompt templates adaptés au modèle Exercise existant.

Correspondances :
  Exercise.solution        ← ce qu'on appelle "solution_template" dans les prompts
  TestCase.input_data      ← "input"
  TestCase.expected_output ← "expected_output"
  TestCase.description     ← "description"
  TestCase.order           ← index du tableau

Difficultés en français : facile / moyen / difficile
"""
from langchain_core.prompts import ChatPromptTemplate

SYSTEM_PROMPT = """\
Tu es un expert en informatique et en pédagogie.
Ta mission est de générer des exercices de code de haute qualité.
Un bon exercice est :
- Clair et non ambigu
- Adapté au niveau de difficulté demandé
- Cohérent (les tests correspondent bien à la description)
- Rédigé dans le langage cible

Tu DOIS répondre uniquement avec un objet JSON valide, sans markdown, sans explication.
"""

# ---------------------------------------------------------------------------
# Prompt de génération
# ---------------------------------------------------------------------------
GENERATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", """\
Génère un exercice de code avec ces contraintes :

- Langage    : {language}
- Difficulté : {difficulty}  (facile | moyen | difficile)
- Sujet      : {topic}
- Instructions supplémentaires : {extra_instructions}

Retourne un objet JSON avec EXACTEMENT ces champs :
{{
  "title": "Titre court et descriptif (max 80 caractères)",
  "description": "Description complète en Markdown. Inclure le contexte, les contraintes, un exemple entrée/sortie.",
  "solution": "Code de départ en {language} avec des marqueurs TODO où l'étudiant doit compléter. Syntaxiquement valide.",
  "test_cases": [
    {{
      "input_data": "valeur d'entrée exacte (chaîne, nombre, ou JSON sérialisé)",
      "expected_output": "sortie attendue exacte",
      "description": "Ce que ce test vérifie"
    }}
  ]
}}

Règles importantes :
- Fournis au moins 3 tests (dont des cas limites).
- La solution doit avoir des marqueurs TODO clairs là où l'étudiant code.
- La description doit être auto-suffisante (sans référence externe).
- Toutes les entrées/sorties des tests doivent être cohérentes entre elles.
- Pour {language}, respecte les conventions du langage (indentation, types, etc.).
"""),
])

# ---------------------------------------------------------------------------
# Prompt de validation
# ---------------------------------------------------------------------------
VALIDATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """\
Tu es un relecteur rigoureux d'exercices de code.
Réponds UNIQUEMENT avec un objet JSON. Pas de markdown, pas de texte supplémentaire.
"""),
    ("human", """\
Évalue la qualité et la cohérence de cet exercice :

--- EXERCICE ---
Titre      : {title}
Langage    : {language}
Difficulté : {difficulty}
Description :
{description}

Solution (template étudiant) :
{solution}

Tests :
{test_cases}
--- FIN ---

Retourne un JSON :
{{
  "is_valid": true ou false,
  "score": 0-100,
  "clarity_score": 0-100,
  "consistency_score": 0-100,
  "issues": ["problème 1", "problème 2"],
  "suggestions": ["suggestion 1", "suggestion 2"]
}}

Critères :
- Le titre reflète bien le contenu
- La description est claire et complète
- La solution est du {language} valide avec des TODO
- Les tests sont cohérents avec la description
- La difficulté correspond au niveau demandé
- Score >= 75 = exercice valide
"""),
])

# ---------------------------------------------------------------------------
# Prompt de correction
# ---------------------------------------------------------------------------
REGENERATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", """\
L'exercice suivant a échoué la revue qualité. Corrige TOUS les problèmes
et retourne la version corrigée en JSON (même schéma qu'avant).

--- EXERCICE ORIGINAL ---
{original_exercise}

--- PROBLÈMES DÉTECTÉS ---
{issues}

--- SUGGESTIONS ---
{suggestions}

Retourne l'exercice corrigé en JSON avec les champs :
title, description, solution, test_cases
"""),
])
