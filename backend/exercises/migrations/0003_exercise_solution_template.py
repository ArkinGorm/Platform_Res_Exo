from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        # Remplace par le nom exact de ta dernière migration
        ('exercises', '0002_exercise_ai_generated_exercise_ai_model_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='exercise',
            name='solution_template',
            field=models.TextField(blank=True, default=''),
            preserve_default=False,
        ),
    ]
