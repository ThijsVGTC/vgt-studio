from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def gebarometer_overview(request):
    return render(
        request,
        "gebarometer/overview.html",
    )