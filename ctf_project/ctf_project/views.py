from django.shortcuts import redirect

def index(request):
    if request.user.is_authenticated:
        # Redirect authenticated users to the challenges page
        return redirect("challenges:index")  # or the appropriate name for the challenges page
    else:
        # Redirect unauthenticated users to the login page
        return redirect("accounts:login")