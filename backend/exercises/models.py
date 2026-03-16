from django.db import models
from django.conf import settings

class Exercise(models.Model):
    DIFFICULTY_CHOICES = (
        ('facile', 'Facile'),
        ('moyen', 'Moyen'),
        ('difficile', 'Difficile'),
    )
    LANGUAGE_CHOICES = (
        ('javascript', 'JavaScript'),
        ('python', 'Python'),
        ('java', 'Java'),
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='facile')
    language = models.CharField(max_length=20, choices=LANGUAGE_CHOICES, default='javascript')
    solution = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title

class TestCase(models.Model):
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='test_cases')
    input_data = models.TextField()
    expected_output = models.TextField()
    description = models.CharField(max_length=255, blank=True)
    order = models.IntegerField(default=0)