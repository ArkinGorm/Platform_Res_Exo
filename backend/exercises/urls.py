from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ExerciseViewSet


router = DefaultRouter()
# On enregistre avec un préfixe vide car 'exercises/' est déjà dans l'URL principal conflit avec l'import ai_urlspattern réglé.
router.register(r'', ExerciseViewSet, basename='exercise')

urlpatterns = [
    path('', include(router.urls)),
    path('ai/', include('exercises.Auto_Gen.urls_ai')),
]