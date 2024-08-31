import matplotlib.pyplot 
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO
from django.db.models import Sum, Case, When
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Challenge, Submission, Team, ScoreHistory
from django.contrib.auth.models import User
import base64
import pytz

def index(request):
    if request.user.is_authenticated:
        return redirect("challenges:feeds")  
    else:
        return redirect("accounts:login")

@login_required
def feeds(request):
    user = request.user
    
    # Get the user's team
    team = user.team_set.first()
    if not team:
        # Handle the case where the user is not in any team
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

    # Calculate the number of solvers for this challenge
    num_solvers = Submission.objects.filter(
        challenge=challenge, correct=True
    ).values('team').distinct().count()

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
            update_all_users_points()
        else:
            messages.error(request, 'Incorrect flag. Try again!')

        return redirect('challenges:challenge_detail', challenge_id=challenge.id)

    context = {
        'challenge': challenge,
        'num_solvers': num_solvers,
        'solved': solved,
    }

    return render(request, 'challenges/challenge_detail.html', context)

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

        # Check if the team has already submitted a correct flag for this challenge
        existing_submission = Submission.objects.filter(team=team, challenge=challenge).first()
        if existing_submission:
            if existing_submission.correct:
                messages.error(request, 'You have already solved this challenge!')
                return redirect('challenges:challenge_detail', challenge_id=challenge.id)
            else:
                # Allow re-submission if the previous attempt was incorrect
                correct = (challenge.flag == submitted_flag)
                existing_submission.submitted_flag = submitted_flag
                existing_submission.correct = correct
                existing_submission.user = user
                existing_submission.save()

                if correct:
                    messages.success(request, 'Correct flag!')
                    update_all_users_points()
                else:
                    messages.error(request, 'Incorrect flag. Try again!')
                
                return redirect('challenges:challenge_detail', challenge_id=challenge.id)
        else:
            # Handle new submission
            correct = (challenge.flag == submitted_flag)
            try:
                submission = Submission(
                    team=team,
                    challenge=challenge,
                    submitted_flag=submitted_flag,
                    correct=correct,
                    user=user
                )
                submission.save()
                if correct:
                    messages.success(request, 'Correct flag!')
                    update_all_users_points()
                else:
                    messages.error(request, 'Incorrect flag. Try again!')
            except Exception as e:
                messages.error(request, f'An error occurred: {e}')
        
        # Redirect to the challenge detail page after submission
        return redirect('challenges:challenge_detail', challenge_id=challenge.id)

    # If the request method is not POST, redirect to the challenges index page
    return redirect('challenges:index')

def update_all_users_points():
    for team in Team.objects.all():
        total_points = Submission.objects.filter(team=team, correct=True).aggregate(Sum('challenge__points'))['challenge__points__sum'] or 0
        ScoreHistory.objects.create(team=team, points=total_points)

@login_required
def leaderboard(request):
    user = request.user

    # Calculate total points for each team
    teams = Team.objects.annotate(
        total_points=Sum(Case(
            When(submission__correct=True, then='submission__challenge__points'),
            default=0
        ))
    ).order_by('-total_points', 'name')

    # Prepare data for time series graph
    team_time_series_data = {}

    for team in Team.objects.all():
        score_histories = ScoreHistory.objects.filter(team=team).order_by('timestamp')
        time_series_data = {}

        for score_history in score_histories:
            time_series_data[score_history.timestamp] = score_history.points
        
        if time_series_data:
            sorted_times = sorted(time_series_data.keys())
            sorted_points = [time_series_data[time] for time in sorted_times]
            team_time_series_data[team.name] = (sorted_times, sorted_points)

    # Create the plot
    fig, ax = plt.subplots(figsize=(20, 10))

    colors = plt.cm.get_cmap('tab10', len(team_time_series_data))
    
    for i, (team_name, (times, points)) in enumerate(team_time_series_data.items()):
        ax.plot(times, points, marker='o', color=colors(i), label=team_name, linewidth=5)

    ax.set_xlabel('Time', fontsize=20)
    ax.set_ylabel('Total Points', fontsize=18)
    ax.set_title('Points Over Time', fontsize=22)
    ax.legend(fontsize=20)
    seoul_tz = pytz.timezone('Asia/Seoul')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M', tz=seoul_tz))
    ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=5))
    fig.autofmt_xdate()

    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    leaderboard_graph = base64.b64encode(buf.getvalue()).decode('utf-8')
    plt.close(fig)

    rankings = [(i + 1, team.name, team.total_points) for i, team in enumerate(teams)]

    context = {
        'teams': teams,
        'leaderboard_graph': leaderboard_graph,
        'rankings': rankings,
    }

    return render(request, 'challenges/leaderboard.html', context)

@login_required
def problem_stats(request):
    user = request.user
    
    # 문제별 해결 횟수 계산
    challenges = Challenge.objects.all()
    challenge_names = [challenge.title for challenge in challenges]
    solve_counts = [Submission.objects.filter(challenge=challenge, correct=True).count() for challenge in challenges]

    # Generate solve counts bar graph
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

    # Get submissions for the team and calculate submission counts by date
    submissions = Submission.objects.filter(team=team, correct=True).order_by('submitted_at')
    dates = [submission.submitted_at.date() for submission in submissions]
    date_counts = {}
    for date in dates:
        if date in date_counts:
            date_counts[date] += 1
        else:
            date_counts[date] = 1

    # Generate submission counts line graph
    fig, ax = plt.subplots(figsize=(12, 6))

    sorted_dates = sorted(date_counts.keys())
    sorted_counts = [date_counts[date] for date in sorted_dates]

    ax.plot(sorted_dates, sorted_counts, marker='o', linestyle='-', color='b')

    ax.set_title('Correct Submissions Over Time')
    ax.set_xlabel('Date')
    ax.set_ylabel('Number of Correct Submissions')

    # Format x-axis to show date labels clearly
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
