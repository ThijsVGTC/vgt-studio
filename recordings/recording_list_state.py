from datetime import date, datetime

from django.utils import timezone


RECORDING_TABS = (
    ("unplanned", "Leeg / ongepland"),
    ("planned", "Gepland"),
    ("completed", "Voltooid"),
    ("skipped", "Overgeslagen"),
    ("unlinked", "Zonder Signbank-entry"),
)


def parse_recording_date(value):
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    value = (value or "").strip()

    if not value:
        return None

    for date_format in (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
    ):
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue

    return None


def get_recording_state(item, today=None):
    if today is None:
        today = timezone.localdate()

    planned_date = parse_recording_date(item.recording_date)
    review = item.review_status or ""
    workflow = item.recording_workflow_status or ""
    video_status = item.new_video_status or ""

    needs_retake = (
        review == "OPNAME_AFGEKEURD"
        or (
            review not in {
                "OPGENOMEN",
                "OVER-OPM",
                "OVER-AL_VIDEO",
            }
            and (
                workflow == "REJECTED"
                or video_status == "AFGEKEURD"
            )
        )
    )

    if item.signbank_entry_id is None:
        tab = "unlinked"

    elif not needs_retake and review in {
        "OVER-OPM",
        "OVER-AL_VIDEO",
    }:
        tab = "skipped"

    elif not needs_retake and (
        review == "OPGENOMEN"
        or workflow == "COMPLETED"
    ):
        tab = "completed"

    elif planned_date is not None and planned_date >= today:
        tab = "planned"

    else:
        tab = "unplanned"

    return {
        "tab": tab,
        "label": dict(RECORDING_TABS)[tab],
        "plannedDate": (
            planned_date.isoformat()
            if planned_date is not None
            else None
        ),
        "overdue": (
            tab == "unplanned"
            and planned_date is not None
            and planned_date < today
        ),
        "invalidDate": (
            bool(item.recording_date)
            and planned_date is None
        ),
        "needsRetake": needs_retake,
    }