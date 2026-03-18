from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ExerciseViewSet

router = DefaultRouter()
# On enregistre avec un préfixe vide car 'exercises/' est déjà dans l'URL principal
router.register(r'', ExerciseViewSet, basename='exercise')

urlpatterns = [
    path('', include(router.urls)),
]