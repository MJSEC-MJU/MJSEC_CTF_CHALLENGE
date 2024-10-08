# Generated by Django 5.1 on 2024-08-31 09:31

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('challenges', '0008_challenge_file_challenge_url_team_scorehistory_team_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name='scorehistory',
            name='team',
        ),
        migrations.RemoveField(
            model_name='scorehistory',
            name='user',
        ),
        migrations.AlterUniqueTogether(
            name='submission',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='team',
            name='total_points',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='challenge',
            name='end_time',
            field=models.DateTimeField(),
        ),
        migrations.AddConstraint(
            model_name='submission',
            constraint=models.UniqueConstraint(fields=('user', 'challenge'), name='unique_user_challenge'),
        ),
        migrations.DeleteModel(
            name='ScoreHistory',
        ),
    ]
