import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO
from django.db.models import Sum, Case, When
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Challenge, Submission, Team
import base64
import datetime
import pytz
import plotly.graph_objs as go
from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import Submission, Team
from collections import defaultdict
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
def index(request):
    if request.user.is_authenticated:
        return redirect("challenges:feeds")  
    else:
        return redirect("accounts:login")

@login_required
def feeds(request):
    user = request.user
    team = user.team_set.first()

    if not team:
        challenges = Challenge.objects.all()
        solved_challenges = []
    else:
        challenges = Challenge.objects.all()
        solved_challenges = Submission.objects.filter(team=team, correct=True).values_list('challenge_id', flat=True)
    
    context = {
        'challenges': challenges,
        'solved_challenges': solved_challenges,
    }
    return render(request, 'challenges/feeds.html', context)

@login_required
def challenge_detail(request, challenge_id):
    user = request.user
    team = user.team_set.first()

    if not team:
        messages.error(request, 'You are not part of any team.')
        return redirect("challenges:feeds")
    
    challenge = get_object_or_404(Challenge, pk=challenge_id)
    solved = Submission.objects.filter(team=team, challenge=challenge, correct=True).exists()
    num_solvers = Submission.objects.filter(challenge=challenge, correct=True).values('team').distinct().count()

    if request.method == 'POST':
        submitted_flag = request.POST['flag']
        correct = (challenge.flag == submitted_flag)

        submission, created = Submission.objects.update_or_create(
            team=team,
            challenge=challenge,
            defaults={'submitted_flag': submitted_flag, 'correct': correct, 'user': user}
        )

        if correct:
            messages.success(request, 'Correct flag!')
            update_team_points(team)
        else:
            messages.error(request, 'Incorrect flag. Try again!')

        return redirect('challenges:challenge_detail', challenge_id=challenge.id)

    context = {
        'challenge': challenge,
        'num_solvers': num_solvers,
        'solved': solved,
    }
    return render(request, 'challenges/challenge_detail.html', context)


from django.db import transaction
from django.utils import timezone
from datetime import timedelta

@login_required
def submit_flag(request):
    user = request.user
    team = user.team_set.first()

    if not team:
        messages.error(request, 'You are not part of any team.')
        return redirect("challenges:feeds")

    if request.method == 'POST':
        challenge_id = request.POST.get('challenge_id')
        submitted_flag = request.POST.get('flag')

        if not challenge_id or not submitted_flag:
            messages.error(request, 'Challenge ID and flag must be provided.')
            return redirect('challenges:challenge_detail', challenge_id=challenge_id)

        challenge = get_object_or_404(Challenge, pk=challenge_id)

        # 팀의 최근 제출 시간 확인 (동일 챌린지에 대해)
        last_team_submission = Submission.objects.filter(team=team, challenge=challenge).order_by('-submitted_at').first()

        if last_team_submission:
            now = timezone.now()
            # 30초 이내에 제출한 경우 제출을 막음
            if last_team_submission.submitted_at and now - last_team_submission.submitted_at < timedelta(seconds=30):
                remaining_time = 30 - (now - last_team_submission.submitted_at).seconds
                messages.error(request, f'Your team has recently submitted. Please wait {remaining_time} seconds before trying again.')
                return redirect('challenges:challenge_detail', challenge_id=challenge.id)

        try:
            with transaction.atomic():  # 트랜잭션 시작
                # 동시성 문제 해결을 위해 팀의 제출 데이터를 락으로 보호
                existing_submission = Submission.objects.select_for_update().filter(team=team, challenge=challenge).first()

                if existing_submission:
                    if existing_submission.correct:
                        messages.error(request, 'You have already solved this challenge!')
                        return redirect('challenges:challenge_detail', challenge_id=challenge.id)
                    else:
                        # 제출 시간 확인 및 30초 딜레이 처리
                        now = timezone.now()
                        if existing_submission.submitted_at and now - existing_submission.submitted_at < timedelta(seconds=30):
                            remaining_time = 30 - (now - existing_submission.submitted_at).seconds
                            messages.error(request, f'Please wait {remaining_time} seconds before trying again.')
                            return redirect('challenges:challenge_detail', challenge_id=challenge.id)

                        # 정답 확인 및 제출 갱신
                        correct = (challenge.flag == submitted_flag)
                        existing_submission.submitted_flag = submitted_flag
                        existing_submission.correct = correct
                        existing_submission.submitted_at = now
                        existing_submission.user = user
                        existing_submission.save()

                        if correct:
                            messages.success(request, 'Correct flag!')
                            update_team_points(team)
                        else:
                            messages.error(request, 'Incorrect flag. Try again!')

                        # 점수 업데이트
                        challenge.update_challenge_score()  # 점수 업데이트
                        return redirect('challenges:challenge_detail', challenge_id=challenge.id)

                else:
                    correct = (challenge.flag == submitted_flag)
                    submission = Submission(
                        team=team,
                        challenge=challenge,
                        submitted_flag=submitted_flag,
                        correct=correct,
                        user=user,
                        submitted_at=timezone.now()
                    )
                    submission.save()

                    if correct:
                        messages.success(request, 'Correct flag!')
                        update_team_points(team)
                    else:
                        messages.error(request, 'Incorrect flag. Try again!')

                    # 점수 업데이트
                    challenge.update_challenge_score()  # 점수 업데이트

        except Exception as e:
            messages.error(request, f'An error occurred during submission: {e}')

        return redirect('challenges:challenge_detail', challenge_id=challenge.id)

    return redirect('challenges:index')



@receiver(post_delete, sender=Submission)
def update_team_points_on_delete(sender, instance, **kwargs):
    team = instance.team
    update_team_points(team)

def update_team_points(team):
    total_points = Submission.objects.filter(team=team, correct=True).aggregate(
        total_points=Sum('challenge__points')
    )['total_points'] or 0
    team.total_points = total_points
    team.save()
@login_required
def leaderboard(request):
    # Update teams to ensure they have the latest total points
    teams = Team.objects.all()
    for team in teams:
        update_team_points(team)  # Ensure points are updated before rendering

    # Sort teams by total points and name
    teams = teams.order_by('-total_points', 'name')

    user_stats = []
    team_time_series_data = {}
    submissions = Submission.objects.filter(correct=True).select_related('team')
    user_dict = defaultdict(lambda: {'count': 0, 'last_submission_time': None, 'points': 0})

    for submission in submissions:
        user = submission.user
        user_dict[user]['count'] += 1
        user_dict[user]['points'] += submission.challenge.points
        # First submission time
        if user_dict[user]['last_submission_time'] is None or submission.submitted_at > user_dict[user]['last_submission_time']:
            user_dict[user]['last_submission_time'] = submission.submitted_at

    for user, stats in user_dict.items():
        user_stats.append((user.username, stats['count'], stats['points'], stats['last_submission_time']))

    user_stats.sort(key=lambda x: (-x[2], x[3] if x[3] is not None else datetime.datetime.max))

    for team in teams:
        submissions = Submission.objects.filter(team=team, correct=True).order_by('submitted_at')
        time_series_data = defaultdict(int)

        for submission in submissions:
            timestamp = submission.submitted_at
            points = submission.challenge.points
            time_series_data[timestamp] += points
        
        sorted_times = sorted(time_series_data.keys())
        sorted_points = [time_series_data[time] for time in sorted_times]
        
        cumulative_points = []
        running_total = 0
        for points in sorted_points:
            running_total += points
            cumulative_points.append(running_total)
        
        team_time_series_data[team.name] = (sorted_times, cumulative_points)

    traces = []
    colors = ['#FF5733', '#33FF57', '#3357FF', '#F3FF33', '#FF33F6']

    for i, (team_name, (times, points)) in enumerate(team_time_series_data.items()):
        trace = go.Scatter(
            x=[time.isoformat() for time in times],
            y=points,
            mode='lines+markers',
            name=team_name,
            line=dict(color=colors[i % len(colors)]),
        )
        traces.append(trace)

    layout = go.Layout(
        title='Points Over Time',
        xaxis=dict(title='Time', tickformat='%H:%M'),
        yaxis=dict(title='Total Points'),
        plot_bgcolor='#ffffff',
        paper_bgcolor='#ffffff',
        font=dict(color='#333333'),
        xaxis_title_font=dict(color='#333333'),
        yaxis_title_font=dict(color='#333333'),
    )
    
    fig = go.Figure(data=traces, layout=layout)
    leaderboard_graph = fig.to_json()

    rankings = [(i + 1, team.name, team.total_points) for i, team in enumerate(teams)]
   
    context = {
        'teams': teams,
        'leaderboard_graph': leaderboard_graph,
        'rankings': rankings,
        'mvp': user_stats,
    }

    return render(request, 'challenges/leaderboard.html', context)

@login_required
def problem_stats(request):
    challenges = Challenge.objects.all()
    challenge_names = [challenge.title for challenge in challenges]
    solve_counts = [Submission.objects.filter(challenge=challenge, correct=True).count() for challenge in challenges]

    fig, ax = plt.subplots()
    ax.barh(challenge_names, solve_counts, color='skyblue')
    ax.set_xlabel('Number of Correct Submissions')
    ax.set_title('Problem Solving Stats')

    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    problem_stats_graph = base64.b64encode(buf.getvalue()).decode('utf-8')
    plt.close(fig)

    context = {
        'problem_stats_graph': problem_stats_graph
    }

    return render(request, 'challenges/problem_stats.html', context)

@login_required
def submission_stats(request):
    user = request.user
    team = user.team_set.first()

    if not team:
        messages.error(request, 'You are not part of any team.')
        return redirect("challenges:feeds")

    submissions = Submission.objects.filter(team=team, correct=True).order_by('submitted_at')
    dates = [submission.submitted_at.date() for submission in submissions]
    date_counts = {}

    for date in dates:
        date_counts[date] = date_counts.get(date, 0) + 1

    fig, ax = plt.subplots(figsize=(12, 6))

    sorted_dates = sorted(date_counts.keys())
    sorted_counts = [date_counts[date] for date in sorted_dates]

    ax.plot(sorted_dates, sorted_counts, marker='o', linestyle='-', color='b')
    ax.set_title('Correct Submissions Over Time')
    ax.set_xlabel('Date')
    ax.set_ylabel('Number of Correct Submissions')

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax.xaxis.set_major_locator(mdates.DayLocator())
    fig.autofmt_xdate()

    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    submission_stats_graph = base64.b64encode(buf.getvalue()).decode('utf-8')
    plt.close(fig)

    context = {
        'submission_stats_graph': submission_stats_graph
    }

    return render(request, 'challenges/submission_stats.html', context)
