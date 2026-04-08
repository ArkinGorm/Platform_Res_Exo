"""
Je l'ajoute a mon urlpatern de exercises/urls.py pour que les urls de l'ia soient accessibles. 
"""
from django.urls import path
from exercises.Auto_Gen.views_ai import (
    GenerateExerciseView,
    GenerationRequestDetailView,
    UserGenerationHistoryView,
    list_ai_providers,
)

# Include this list in your exercises/urls.py urlpatterns
urlpatterns = [
    path("generate/",              GenerateExerciseView.as_view(),        name="exercise-generate"),
    path("generate/providers/",    list_ai_providers,                     name="exercise-generate-providers"),
    path("generate/history/",      UserGenerationHistoryView.as_view(),   name="exercise-generate-history"),
    path("generate/<int:pk>/",     GenerationRequestDetailView.as_view(), name="exercise-generate-detail"),
]

