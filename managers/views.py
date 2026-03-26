from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def manager_dashboard(request):
    return render(request, 'managers/dashboard.html')
