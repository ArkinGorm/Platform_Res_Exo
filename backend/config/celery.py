import os
from celery import Celery

# Définir le module de settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

# Utiliser Redis comme broker
app.config_from_object('django.conf:settings', namespace='CELERY')

# Découvrir automatiquements les tâches dans les applications installées
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')