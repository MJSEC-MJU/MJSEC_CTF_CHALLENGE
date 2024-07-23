from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Challenge(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    flag = models.CharField(max_length=200)
    points = models.IntegerField(default=0)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title

class Submission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE)
    submitted_flag = models.CharField(max_length=200)
    submitted_at = models.DateTimeField(auto_now_add=True)
    correct = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'challenge')

    def __str__(self):
        return f'{self.user.username} - {self.challenge.title}'

class ScoreHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    points = models.IntegerField(default=0)
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f'{self.user.username} - {self.points} at {self.timestamp}'
