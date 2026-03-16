from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ExerciseViewSet

router = DefaultRouter()
router.register(r'exercises', ExerciseViewSet)

urlpatterns = [
    path('', include(router.urls)),

    path('published/', ExerciseViewSet.as_view({'get': 'published'}), name='published'),
]