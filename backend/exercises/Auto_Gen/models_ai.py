"""
Ajoute ExerciseGenerationRequest dans exercises/models.py
"""
from django.db import models
from django.conf import settings


class ExerciseGenerationRequest(models.Model):
    """Trace chaque demande de génération IA — config, statut, résultat."""

    class Status(models.TextChoices):
        PENDING   = "pending",   "En attente"
        RUNNING   = "running",   "En cours"
        COMPLETED = "completed", "Terminé"
        FAILED    = "failed",    "Échoué"

    # Mirrors Exercise choices
    DIFFICULTY_CHOICES = (
        ('facile',    'Facile'),
        ('moyen',     'Moyen'),
        ('difficile', 'Difficile'),
    )
    LANGUAGE_CHOICES = (
        ('javascript', 'JavaScript'),
        ('python',     'Python'),
        ('java',       'Java'),
    )

    # --- Config ---
    provider           = models.CharField(max_length=50, default="gemini")
    model              = models.CharField(max_length=100, blank=True)
    temperature        = models.FloatField(default=0.7)
    language           = models.CharField(max_length=20, choices=LANGUAGE_CHOICES)
    difficulty         = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    topic              = models.TextField()
    extra_instructions = models.TextField(blank=True)
    auto_publish       = models.BooleanField(default=False)

    # --- Suivi ---
    status           = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    celery_task_id   = models.CharField(max_length=255, blank=True)
    attempts         = models.PositiveSmallIntegerField(default=0)
    error_message    = models.TextField(blank=True)
    validation_score = models.PositiveSmallIntegerField(null=True, blank=True)

    # --- Timestamps ---
    created_at   = models.DateTimeField(auto_now_add=True)
    started_at   = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # --- Relations ---
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="generation_requests",
    )
    exercise = models.OneToOneField(
        "exercises.Exercise",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="generation_request",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Demande de génération"
        verbose_name_plural = "Demandes de génération"

    def __str__(self):
        return f"[{self.status}] {self.provider} · {self.language} · {self.difficulty} — {self.topic[:40]}"

    @property
    def is_done(self):
        return self.status in (self.Status.COMPLETED, self.Status.FAILED)


# -----------------------------------------------------------------------
# Ajoute ces 3 champs à ton Exercise existant puis lance makemigrations :
#
#   ai_generated = models.BooleanField(default=False)
#   ai_provider  = models.CharField(max_length=50, blank=True)
#   ai_model     = models.CharField(max_length=100, blank=True)
# -----------------------------------------------------------------------
