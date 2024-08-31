from django.contrib import admin
from .models import Challenge, Submission,ScoreHistory, Team
from django.contrib import messages

@admin.action(description='Reset Graph Data')
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ('title', 'description', 'points', 'start_time', 'end_time', 'file', 'url')
    search_fields = ('title', 'description')

class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('team', 'challenge', 'submitted_flag', 'submitted_at', 'correct')
    list_filter = ('team', 'challenge', 'correct')
    search_fields = ('team__name', 'challenge__title', 'submitted_flag')

class ScoreHistoryAdmin(admin.ModelAdmin):
    list_display = ('team', 'points', 'timestamp')
    list_filter = ('team',)
    search_fields = ('team__name',)

# 관리자 페이지에 모델 등록
admin.site.register(Challenge, ChallengeAdmin)
admin.site.register(Submission, SubmissionAdmin)
admin.site.register(ScoreHistory, ScoreHistoryAdmin)
admin.site.register(Team)