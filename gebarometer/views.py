import calendar
from datetime import date
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from .models import GebarometerItem


DUTCH_MONTH_NAMES = [
    "",
    "januari",
    "februari",
    "maart",
    "april",
    "mei",
    "juni",
    "juli",
    "augustus",
    "september",
    "oktober",
    "november",
    "december",
]


@login_required
def gebarometer_overview(request):
    today = date.today()

    try:
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))

        if month < 1 or month > 12:
            raise ValueError

    except (TypeError, ValueError):
        year = today.year
        month = today.month

    calendar_object = calendar.Calendar(firstweekday=0)

    month_days = calendar_object.monthdatescalendar(
        year,
        month,
    )

    first_day = date(year, month, 1)

    if month == 12:
        next_month_date = date(year + 1, 1, 1)
    else:
        next_month_date = date(year, month + 1, 1)

    items = (
        GebarometerItem.objects
        .filter(
            planned_date__gte=first_day,
            planned_date__lt=next_month_date,
        )
        .select_related("signbank_entry")
        .order_by("planned_date", "position", "id")
    )

    items_by_date = {}

    for item in items:
        items_by_date.setdefault(
            item.planned_date,
            [],
        ).append(item)

    calendar_weeks = []

    for week in month_days:
        week_data = []

        for day in week:
            week_data.append(
                {
                    "date": day,
                    "in_current_month": day.month == month,
                    "is_today": day == today,
                    "items": items_by_date.get(day, []),
                }
            )

        calendar_weeks.append(week_data)

    previous_month = month - 1
    previous_year = year

    if previous_month == 0:
        previous_month = 12
        previous_year -= 1

    next_month = month + 1
    next_year = year

    if next_month == 13:
        next_month = 1
        next_year += 1

    context = {
        "year": year,
        "month": month,
        "month_name": DUTCH_MONTH_NAMES[month],
        "calendar_weeks": calendar_weeks,
        "today": today,
        "previous_year": previous_year,
        "previous_month": previous_month,
        "next_year": next_year,
        "next_month": next_month,
    }

    return render(
        request,
        "gebarometer/overview.html",
        context,
    )

@login_required
def gebarometer_detail(request, pk):
    item = get_object_or_404(
        GebarometerItem.objects.select_related("signbank_entry"),
        pk=pk,
    )

    context = {
        "item": item,
    }

    return render(
        request,
        "gebarometer/detail.html",
        context,
    )