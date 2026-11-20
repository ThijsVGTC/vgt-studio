from collections import Counter

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Prefetch, Q, prefetch_related_objects
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET
from zoneinfo import ZoneInfo
from .models import RecordingItem, RecordingSeriesItem, SignbankEntry
from .recording_list_data import serialize_recording_item
from .recording_list_state import (
    RECORDING_TABS,
    get_recording_state,
    parse_recording_date,
)


@login_required
@require_GET
def recording_list_data(request):
    from .views import serialize_signbank_row

    filters = {
        key: request.GET.get(key, "").strip()
        for key in (
            "q",
            "status",
            "recording_by",
            "recording_date",
            "review_status",
            "variant",
        )
    }

    tab = request.GET.get("tab", "unplanned")

    if tab not in dict(RECORDING_TABS):
        tab = "unplanned"

    sort = request.GET.get("sort", "gloss")

    if sort not in {"gloss", "signbank_id", "recording_date"}:
        sort = "gloss"

    direction = (
        "desc"
        if request.GET.get("direction") == "desc"
        else "asc"
    )

    base = RecordingItem.objects.all()
    items = base.select_related("signbank_entry")

    for key in (
        "status",
        "recording_by",
        "recording_date",
        "review_status",
    ):
        if filters[key]:
            items = items.filter(**{key: filters[key]})

    if filters["variant"]:
        matching_ids = [
            pk
            for pk, variants in (
                SignbankEntry.objects.values_list("pk", "variants")
            )
            if filters["variant"] in (variants or [])
        ]

        items = items.filter(
            signbank_entry_id__in=matching_ids
        )

    if filters["q"]:
        query = filters["q"]

        search = (
            Q(signbank_entry__gloss__icontains=query)
            | Q(
                signbank_entry__isnull=True,
                gloss_id__icontains=query,
            )
            | Q(
                signbank_entry__mogelijke_vertaling__icontains=query
            )
            | Q(signbank_entry__labels__icontains=query)
            | Q(status__icontains=query)
            | Q(recording_by__icontains=query)
            | Q(recording_date__icontains=query)
            | Q(remarks__icontains=query)
            | Q(video_review_remarks__icontains=query)
        )

        if query.isdigit():
            search |= Q(signbank_id=int(query))

        items = items.filter(search)

    today = timezone.localdate(
        timezone=ZoneInfo("Europe/Brussels")
    )
    matching = list(items.order_by("signbank_id"))

    states = {
        item.pk: get_recording_state(item, today=today)
        for item in matching
    }

    counts = Counter(
        state["tab"]
        for state in states.values()
    )

    selected = [
        item
        for item in matching
        if states[item.pk]["tab"] == tab
    ]

    def gloss_key(item):
        gloss = (
            item.signbank_entry.gloss
            if item.signbank_entry_id
            else item.gloss_id
        )

        return (gloss.casefold(), item.signbank_id)

    descending = direction == "desc"

    if sort == "signbank_id":
        selected.sort(
            key=lambda item: item.signbank_id,
            reverse=descending,
        )

    elif sort == "recording_date":
        dated = [
            item
            for item in selected
            if states[item.pk]["plannedDate"]
        ]

        undated = [
            item
            for item in selected
            if not states[item.pk]["plannedDate"]
        ]

        dated.sort(
            key=lambda item: (
                parse_recording_date(item.recording_date),
                gloss_key(item),
            ),
            reverse=descending,
        )

        undated.sort(key=gloss_key)
        selected = dated + undated

    else:
        selected.sort(
            key=gloss_key,
            reverse=descending,
        )

    page = Paginator(selected, 50).get_page(
        request.GET.get("page", "1")
    )

    prefetch_related_objects(
        page.object_list,
        Prefetch(
            "series_items",
            queryset=(
                RecordingSeriesItem.objects
                .select_related("series")
                .order_by("-series__created_at", "position")
            ),
        ),
    )

    def choices(field):
        return list(
            base
            .exclude(**{field: ""})
            .values_list(field, flat=True)
            .order_by(field)
            .distinct()
        )

    variants = sorted(
        {
            value
            for values in (
                SignbankEntry.objects.values_list(
                    "variants",
                    flat=True,
                )
            )
            for value in (values or [])
            if value
        },
        key=str.casefold,
    )

    return JsonResponse({
        "rows": [
            serialize_recording_item(
                item,
                serialize_signbank_row,
                today=today,
            )
            for item in page.object_list
        ],
        "tab": tab,
        "tabs": [
            {
                "value": value,
                "label": label,
                "count": counts[value],
            }
            for value, label in RECORDING_TABS
        ],
        "filters": filters,
        "sort": sort,
        "direction": direction,
        "page": page.number,
        "pageCount": page.paginator.num_pages,
        "nextPage": (
            page.next_page_number()
            if page.has_next()
            else None
        ),
        "filteredCount": len(selected),
        "totalCount": base.count(),
        "matchingItems": [
            {
                "id": item.pk,
                "signbankId": item.signbank_id,
            }
            for item in selected
        ],
        "options": {
            "statuses": choices("status"),
            "people": choices("recording_by"),
            "dates": choices("recording_date"),
            "variants": variants,
        },
        "csrfToken": get_token(request),
        "urls": {
            "list": reverse("recording_list"),
            "bulkUpdate": reverse("bulk_update_recordings"),
            "startSeries": reverse("start_recording_series"),
            "seriesList": reverse("recording_series_list"),
            "bulkVideoUpload": reverse("bulk_video_upload"),
            "importUrls": reverse("import_urls"),
            "importGoogleSheet": reverse("import_google_sheet"),
            "syncGoogleSheet": reverse("sync_google_sheet"),
        },
    })