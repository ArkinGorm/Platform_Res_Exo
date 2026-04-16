"""
LangChain prompt templates adaptés au modèle Exercise existant.

Correspondances :
  Exercise.solution        ← solution complète + version TODO pour l'étudiant
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
Génère un exercice de code. Réponds UNIQUEMENT avec le JSON demandé.

Contraintes :
- Langage    : {language}
- Difficulté : {difficulty}  (facile | moyen | difficile)
- Sujet      : {topic}
- Instructions : {extra_instructions}

JSON attendu (respecte EXACTEMENT ce schéma) :
{{
  "title": "Titre court (max 80 car.)",
  "description": "Description Markdown auto-suffisante avec contexte, contraintes et un exemple entrée/sortie.",
  "solution": "Code {language} COMPLET et fonctionnel résolvant le problème. La fonction doit s'appeler 'solution'. Pas de TODO ici — c'est la solution de référence servant à faire tourner les tests.",
  "solution_template": "Même squelette que solution mais avec le corps remplacé par des commentaires TODO indiquant à l'étudiant quoi implémenter. La signature de la fonction doit être identique.",
  "test_cases": [
    {{
      "input_data": "valeur exacte (chaîne, nombre ou JSON sérialisé)",
      "expected_output": "sortie exacte correspondante",
      "description": "Phrase courte décrivant CE QUE ce test vérifie (ex: cas nominal, valeur nulle, liste vide…)"
    }}
  ]
}}

Règles :
- Minimum 3 tests unitaires dont au moins 1 cas limite (valeur nulle, liste vide, négatif…).
- Chaque test DOIT avoir une description non vide.
- Toutes les entrées/sorties doivent être cohérentes avec la description.
- La fonction s'appelle toujours "solution" dans les deux champs.
- "solution" est le code complet exécutable — les tests tournent contre cette fonction.
- "solution_template" est ce que verra l'étudiant — corps vide avec TODO.
"""),
])

# ---------------------------------------------------------------------------
# Prompt de validation (LLM-as-judge — utilisé uniquement pour Ollama)
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

Solution de référence (complète) :
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
- La solution est du {language} valide et résout le problème décrit
- Les tests sont cohérents avec la description
- La difficulté correspond au niveau demandé
- Score >= 75 = exercice valide
"""),
])

# ---------------------------------------------------------------------------
# Prompt de correction (compact)
# ---------------------------------------------------------------------------
REGENERATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", """\
Corrige cet exercice qui a échoué la revue qualité. \
Retourne UNIQUEMENT le JSON corrigé (même schéma : title, description, solution, solution_template, test_cases).
Chaque test_case doit avoir une description non vide.
La fonction doit toujours s'appeler "solution".

--- EXERCICE ORIGINAL ---
{original_exercise}

--- PROBLÈMES ---
{issues}

--- SUGGESTIONS ---
{suggestions}
"""),
])
