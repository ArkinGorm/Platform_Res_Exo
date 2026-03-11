from django.db import models
from django.conf import settings

class Submission(models.Model):
    STATUS_CHOICES = (
        ('pending', 'En attente'),
        ('passed', 'Réussi'),
        ('failed', 'Échoué'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    exercise = models.ForeignKey('exercises.Exercise', on_delete=models.CASCADE)
    code = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.exercise.title}"

class TestResult(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='test_results')
    test_case = models.ForeignKey('exercises.TestCase', on_delete=models.CASCADE)
    passed = models.BooleanField(default=False)
    actual_output = models.TextField(blank=True)
    error_message = models.TextField(blank=True)