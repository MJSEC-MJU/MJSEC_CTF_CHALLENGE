from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# 모델 추가: Team
class Team(models.Model):
    name = models.CharField(max_length=200)
    members = models.ManyToManyField(User)
    total_points = models.IntegerField(default=0)
    def __str__(self):
        return self.name

class Challenge(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    flag = models.CharField(max_length=200)
    points = models.IntegerField(default=0)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField()  # Removed default to ensure it's set explicitly
    file = models.FileField(upload_to='challenge_files/', blank=True, null=True)
    url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.title

class Submission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, null=True, blank=True, on_delete=models.SET_NULL)
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE)
    submitted_flag = models.CharField(max_length=200)
    submitted_at = models.DateTimeField(auto_now_add=True)
    correct = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'challenge'], name='unique_user_challenge')
        ]

    def __str__(self):
        return f'{self.user.username} - {self.challenge.title}'

