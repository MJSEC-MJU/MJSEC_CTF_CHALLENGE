from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class CTFConfig(models.Model):
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    class Meta:
        verbose_name = "CTF Schedule"
        verbose_name_plural = "CTF Schedule"

    def __str__(self):
        return "CTF 일정 설정"

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
    points = models.IntegerField(default=500)  # 현재 점수
    min_points = models.IntegerField(default=100)  # 최소 점수
    initial_points = models.IntegerField(default=500)  # 초기 점수
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField()  # 명시적으로 설정되도록 기본값 제거
    file = models.FileField(upload_to='challenge_files/', blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='challenges'
    )
    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # 챌린지를 저장한 후 점수를 조정합니다
        created = self.pk is None
        super().save(*args, **kwargs)
        if created:
            self.update_challenge_score()

    def update_challenge_score(self):
        # 현재 챌린지를 해결한 사용자 수를 계산합니다.
        solved_count = Submission.objects.filter(challenge=self, correct=True).values('user_id').distinct().count()
        # 전체 참가자 수를 계산합니다.
        total_participants = Team.objects.filter(members__isnull=False).distinct().count()
        max_decrement_factor = 0.9

        # 정답 제출자가 없거나 참가 팀이 1팀 이하이면 점수를 변경하지 않습니다.
        if total_participants <= 1 or solved_count <= 1:
            new_points = self.initial_points
        else:
            # 점수 감소 비율 계산 (최소 0으로 유지)
            decrement_factor = max_decrement_factor * (solved_count - 1) / (total_participants - 1)
            decrement_factor = min(max(decrement_factor, 0), max_decrement_factor)

            # 초기 점수에서 점수를 감소시킵니다.
            new_points = self.initial_points * (1 - decrement_factor)
            # 최소 점수 이하로 떨어지지 않도록 합니다.
            new_points = max(new_points, self.min_points)

        # 점수를 업데이트합니다.
        Challenge.objects.filter(pk=self.pk).update(points=new_points)

class Submission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, null=True, blank=True, on_delete=models.SET_NULL)
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE)
    submitted_flag = models.CharField(max_length=200)
    submitted_at = models.DateTimeField(auto_now_add=True)
    correct = models.BooleanField(default=False)
    last_submission_time = models.DateTimeField(auto_now=True)  # 마지막 제출 시간
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'challenge'], name='unique_user_challenge')
        ]

    def __str__(self):
        return f'{self.user.username} - {self.challenge.title}'
