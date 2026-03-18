from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Administrateur'),
        ('participant', 'Participant'),
    )
    first_name = None
    last_name = None
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='participant')
    email = models.EmailField(unique=True)
    
    def __str__(self):
        return f"{self.username} ({self.role})"