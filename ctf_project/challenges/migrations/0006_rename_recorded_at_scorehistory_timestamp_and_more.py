# Generated by Django 4.2.11 on 2024-07-22 22:09

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('challenges', '0005_rename_submitted_at_submission_timestamp_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='scorehistory',
            old_name='recorded_at',
            new_name='timestamp',
        ),
        migrations.RenameField(
            model_name='submission',
            old_name='timestamp',
            new_name='submitted_at',
        ),
    ]
