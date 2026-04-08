from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Administrateur'),
        ('participant', 'Participant'),
    )

    first_name = None
    last_name = None

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='participant'
    )

    email = models.EmailField(unique=True)

    def save(self, *args, **kwargs):
        # Synchronisation automatique du rôle
        if self.is_staff or self.is_superuser:
            self.role = "admin"
        else:
            self.role = "participant"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.role})"