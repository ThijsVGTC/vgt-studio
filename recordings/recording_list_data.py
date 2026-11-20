from django.urls import reverse

from .recording_list_state import get_recording_state


REVIEW_LABELS = {
    "": "Nog niet opgenomen",
    "OPGENOMEN": "Opgenomen",
    "OVER-OPM": "Overgeslagen met opmerking",
    "OVER-AL_VIDEO": "Overgeslagen: bestaande video",
    "OPNAME_AFGEKEURD": "Opname afgekeurd",
}

VIDEO_REVIEW_LABELS = {
    "": "Geen video ter controle",
    "WACHT_OP_CONTROLE": "Wacht op controle",
    "GOEDGEKEURD": "Goedgekeurd",
    "AFGEKEURD": "Afgekeurd",
}


def serialize_recording_item(
    item,
    serialize_signbank_entry,
    today=None,
):
    entry = (
        item.signbank_entry
        if item.signbank_entry_id is not None
        else None
    )

    signbank = (
        serialize_signbank_entry(entry)
        if entry is not None
        else None
    )

    state = get_recording_state(item, today=today)

    # Gebruik actuele Signbank-gegevens zodra er een koppeling is.
    # Bij ontbrekende entries blijven de bewaarde opnamegegevens zichtbaar.
    gloss = entry.gloss if entry is not None else item.gloss_id

    old_video_url = (
        entry.video_url
        if entry is not None
        else item.old_video_url
    )

    thumbnail_url = (
        entry.thumbnail_url
        if entry is not None
        else item.thumbnail_url
    )

    return {
        "id": item.pk,
        "signbankId": item.signbank_id,
        "gloss": gloss,
        "oldVideoUrl": old_video_url,
        "thumbnailUrl": thumbnail_url,
        "recordingUrl": reverse(
            "recording_detail",
            args=[item.signbank_id],
        ),
        "signbankUrl": (
            signbank["detailUrl"]
            if signbank is not None
            else None
        ),
        "signbank": signbank,
        "hasSignbankEntry": entry is not None,
        "signbankSyncedAt": (
            entry.synced_at.isoformat()
            if entry is not None and entry.synced_at
            else None
        ),
        "state": state,
        "status": item.status or "",
        "recordingBy": item.recording_by or "",
        "recordingDate": item.recording_date or "",
        "remarks": item.remarks or "",
        "reviewStatus": item.review_status or "",
        "reviewLabel": REVIEW_LABELS.get(
            item.review_status or "",
            item.review_status or "Onbekend",
        ),
        "workflowStatus": item.recording_workflow_status,
        "newVideoUrl": (
            item.new_video.url
            if item.new_video
            else None
        ),
        "videoReviewStatus": item.new_video_status or "",
        "videoReviewLabel": VIDEO_REVIEW_LABELS.get(
            item.new_video_status or "",
            item.new_video_status or "Onbekend",
        ),
        "videoReviewRemarks": item.video_review_remarks or "",
        "exported": item.signbank_exported,
        "exportedAt": (
            item.signbank_exported_at.isoformat()
            if item.signbank_exported_at
            else None
        ),
        "series": [
            {
                "id": membership.series_id,
                "name": (
                    membership.series.name
                    or f"Opnamereeks {membership.series_id}"
                ),
                "status": membership.series.status,
                "position": membership.position + 1,
                "processed": membership.processed,
                "skipped": membership.skipped,
                "reportUrl": reverse(
                    "recording_series_report",
                    args=[membership.series_id],
                ),
            }
            for membership in item.series_items.all()
        ],
    }