"""
LangChain prompt templates adaptés au modèle Exercise existant.

Correspondances :
  Exercise.solution        ← solution complète + version TODO pour l'étudiant
  TestCase.input_data      ← "input"
  TestCase.expected_output ← "expected_output"
  TestCase.description     ← "description"
  TestCase.order           ← index du tableau

Difficultés en français : facile / moyen / difficile

Types d'exercices :
  - "function"   : solution(*args) → valeur  [défaut]
  - "simulation" : la solution définit une CLASSE (ex: LRUCache, MinStack)
                   input_data  = JSON list de listes [[ClassName, args], [method, args]...]
                   expected    = JSON list de résultats  [null, null, 1, -1, ...]
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

────────────────────────────────────────────────────────────
CHOIX DU TYPE D'EXERCICE :

● TYPE "function" (défaut — exercices algorithmiques simples) :
  La solution est une FONCTION appelée "solution".
  input_data  = valeur Python/JS directe (ex: [2, 3], "hello", 42)
  expected    = résultat direct (ex: "5", "olleh", "True")

● TYPE "simulation" (structures de données, design patterns, OOP) :
  La solution est une CLASSE (ex: LRUCache, MinStack, Queue).
  input_data  = liste JSON de commandes : [["ClassName", ctor_arg], ["method", args...], ...]
  expected    = liste JSON de résultats : [null, null, 1, -1, ...]
                (null pour constructeur et méthodes void, valeur sinon)
  IMPORTANT : Le premier élément est TOUJOURS [ClassName, ...constructorArgs].
              Les résultats void (put, push, set) → null dans expected.

Choisis le type adapté au sujet. Si le sujet parle d'une structure de données
(cache, pile, file, etc.) ou d'un objet avec plusieurs méthodes → TYPE "simulation".
────────────────────────────────────────────────────────────

JSON attendu (respecte EXACTEMENT ce schéma) :
{{
  "type": "function" ou "simulation",
  "title": "Titre court (max 80 car.)",
  "description": "Description Markdown auto-suffisante avec contexte, contraintes et un exemple entrée/sortie.",
  "solution": "Code {language} COMPLET et fonctionnel. Pour 'function' : fonction nommée 'solution'. Pour 'simulation' : classe complète avec toutes les méthodes.",
  "solution_template": "Même squelette mais corps remplacé par des commentaires TODO. Même nom de fonction/classe.",
  "test_cases": [
    {{
      "input_data": "valeur exacte — voir TYPE ci-dessus",
      "expected_output": "sortie exacte correspondante",
      "description": "Phrase courte décrivant CE QUE ce test vérifie"
    }}
  ]
}}

Règles :
- Minimum 3 tests unitaires dont au moins 1 cas limite.
- Chaque test DOIT avoir une description non vide.
- Pour "simulation" : input_data et expected_output sont des tableaux JSON valides.
- Pour "simulation" : expected[0] est TOUJOURS null (constructeur).
- La solution doit être correcte et exécutable sans modification.
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
- Score >= 65 = exercice valide
"""),
])

# ---------------------------------------------------------------------------
# Prompt de correction (compact)
# ---------------------------------------------------------------------------
REGENERATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", """\
Corrige cet exercice qui a échoué la revue qualité. \
Retourne UNIQUEMENT le JSON corrigé (même schéma : type, title, description, solution, solution_template, test_cases).
Chaque test_case doit avoir une description non vide.
Pour "simulation" : input_data et expected_output doivent être des tableaux JSON valides.

--- EXERCICE ORIGINAL ---
{original_exercise}

--- PROBLÈMES ---
{issues}

--- SUGGESTIONS ---
{suggestions}
"""),
])
