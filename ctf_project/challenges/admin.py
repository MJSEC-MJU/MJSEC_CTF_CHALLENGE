from django.contrib import admin
from .models import Challenge, Submission,ScoreHistory
from django.contrib import messages

@admin.action(description='Reset Graph Data')
def reset_graph_data(modeladmin, request, queryset):
    # Logic to reset graph data
    # For example, deleting all submissions
    ScoreHistory.objects.all().delete()
    Submission.objects.all().delete()
    messages.success(request, 'Graph data has been reset.')
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ('title', 'description', 'points', 'start_time', 'end_time')

class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'challenge', 'submitted_flag', 'submitted_at', 'correct')
class ScoreHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'points', 'timestamp')
    actions = [reset_graph_data]
admin.site.register(Challenge, ChallengeAdmin)
admin.site.register(Submission, SubmissionAdmin)
admin.site.register(ScoreHistory, ScoreHistoryAdmin)