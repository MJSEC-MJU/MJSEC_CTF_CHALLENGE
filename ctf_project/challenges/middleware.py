from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone

from .models import CTFConfig


class CTFWindowMiddleware:
    """
    Restrict access before/after the CTF window.
    Allows: admin, static/media, accounts, countdown page itself.
    Before start: redirect to countdown.
    After end: also redirect to countdown (message handled in view).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        allowed_prefixes = [
            '/admin',
            '/static',
            '/media',
        ]
        allowed_exact = {
            reverse('accounts:login'),
            reverse('accounts:logout'),
            reverse('challenges:countdown'),
        }

        # Allow specific prefixes (admin/static/media)
        if any(path.startswith(p) for p in allowed_prefixes) or path in allowed_exact:
            return self.get_response(request)

        config = CTFConfig.objects.first()
        if not config:
            return self.get_response(request)

        now = timezone.now()

        # Before start or after end -> redirect to countdown
        if config.start_time and now < config.start_time:
            return redirect('challenges:countdown')
        if config.end_time and now > config.end_time:
            return redirect('challenges:countdown')

        return self.get_response(request)
