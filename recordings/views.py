import csv
import io
import re
import requests

from pathlib import PurePosixPath
from urllib.parse import urlparse

from django.shortcuts import get_object_or_404, render, redirect
from django.conf import settings
from .models import RecordingItem, AppSettings
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q

# Create your views here.

@login_required
def recording_list(request):
    items = RecordingItem.objects.all()
    selected_status = request.GET.get("status", "")
    selected_recording_by = request.GET.get("recording_by", "")
    selected_recording_date = request.GET.get("recording_date", "")
    selected_review_status = request.GET.get("review_status", "")

    if selected_status:
        items=items.filter(status=selected_status)
    if selected_recording_by:
        items = items.filter(recording_by=selected_recording_by)
    if selected_recording_date:
        items = items.filter(recording_date=selected_recording_date)
    if selected_review_status:
        items = items.filter(review_status=selected_review_status)

    items = items.order_by("signbank_id")

    filtered_ids = list(
        items.values_list("signbank_id", flat=True)
    )


    # Beschikbare waarden voor dropdowns

    statuses = (
        RecordingItem.objects
        .exclude(status="")
        .values_list("status", flat=True)
        .distinct()
        .order_by("status")
    )
    recording_people = (
        RecordingItem.objects
        .exclude(recording_by="")
        .values_list("recording_by", flat=True)
        .distinct()
        .order_by("recording_by")
    )

    recording_dates = (
        RecordingItem.objects
        .exclude(recording_date="")
        .values_list("recording_date", flat=True)
        .distinct()
        .order_by("recording_date")
    )
    return render(
        request,
        "recordings/recording_list.html",
        {
            "items": items,
            "statuses": statuses,
            "recording_people": recording_people,
            "recording_dates": recording_dates,
            "selected_status": selected_status,
            "selected_recording_by": selected_recording_by,
            "selected_recording_date": selected_recording_date,
            "selected_review_status": selected_review_status,
            "filtered_ids": filtered_ids,
        }
    )

@login_required
def start_recording_series(request):
    if request.method != "POST":
        return redirect("recording_list")
    signbank_ids = request.POST.getlist("signbank_ids")
    if not signbank_ids:
        return redirect("recording_list")
    signbank_ids = [int(signbank_id) for signbank_id in signbank_ids]
    request.session["recording_series"] = signbank_ids
    request.session["recording_series_index"] = 0
    request.session["recording_series_filters"]={
        "status": request.POST.get("status", ""),
        "recording_by": request.POST.get("recording_by", ""),
        "recording_date": request.POST.get("recording_date", ""),
        "review_status": request.POST.get("review_status", ""),
    }
    first_id = signbank_ids[0]
    return redirect(
        "recording_detail",
        signbank_id=first_id,
    )

@login_required
def import_urls(request):
    message = ""
    if request.method == "POST":
        pasted_urls = request.POST.get("urls", "")
        urls = pasted_urls.splitlines()
        created = 0
        skipped = 0
        for url in urls:
            url = url.strip()
            if not url:
                continue
            try:
                path = urlparse(url).path
                filename = PurePosixPath(path).name
                if not filename.lower().endswith(".mp4"):
                    skipped += 1
                    continue
                stem = filename[:-4]
                gloss_id, signbank_id = stem.rsplit("-", 1)
                signbank_id = int(signbank_id)
                item, was_created = RecordingItem.objects.get_or_create(
                    signbank_id=signbank_id,
                    defaults={
                        "gloss_id": gloss_id,
                        "old_video_url": url,
                        "status": "pending",
                    },
                )

                if was_created:
                    created += 1
                else:
                    skipped += 1

            except (ValueError, IndexError):
                skipped += 1

        message = f"{created} items toegevoegd. {skipped} overgeslagen."

    return render(
        request,
        "recordings/import_urls.html",
        {"message": message},
    )

@login_required
def import_google_sheet(request):
    message = ""
    if request.method == "POST":
        sheet_url = request.POST.get("sheet_url", "").strip()
        try:
            # Spreadsheet ID vinden
            match = re.search(r"/spreadsheets/d/([^/]+)", sheet_url)
            if not match:
                raise ValueError("Geen geldige Google Spreadsheet-link.")
            spreadsheet_id = match.group(1)
            # gid vinden
            gid_match = re.search(r"gid=(\d+)", sheet_url)
            gid = gid_match.group(1) if gid_match else "0"
            csv_url = (
                f"https://docs.google.com/spreadsheets/d/"
                f"{spreadsheet_id}/export?format=csv&gid={gid}"
            )
            response = requests.get(csv_url, timeout=20)
            response.raise_for_status()
            reader = csv.reader(
                io.StringIO(response.text)
            )
            created = 0
            skipped = 0
            for row in reader:
                if not row:
                    continue
                # We zoeken de eerste cel die een mp4-link bevat
                video_url = None
                for cell in row:
                    cell = cell.strip()
                    if cell.startswith("http") and ".mp4" in cell.lower():
                        video_url = cell
                        break
                if not video_url:
                    continue
                try:
                    path = urlparse(video_url).path
                    filename = PurePosixPath(path).name
                    if not filename.lower().endswith(".mp4"):
                        skipped += 1
                        continue
                    stem = filename[:-4]
                    gloss_id, signbank_id = stem.rsplit("-", 1)
                    signbank_id = int(signbank_id)
                    item, was_created = RecordingItem.objects.get_or_create(
                        signbank_id=signbank_id,
                        defaults={
                            "gloss_id": gloss_id,
                            "old_video_url": video_url,
                            "status": "pending",
                        }
                    )
                    if was_created:
                        created += 1
                    else:
                        skipped += 1
                except (ValueError, IndexError):
                    skipped += 1

            message = (
                f"{created} items toegevoegd. "
                f"{skipped} bestaande of ongeldige items overgeslagen."
            )

        except Exception as e:
            message = f"Fout: {e}"

    return render(
        request,
        "recordings/import_google_sheet.html",
        {"message": message},
    )

@login_required
def sync_google_sheet(request):

    settings, created = AppSettings.objects.get_or_create(pk=1)

    message = ""

    if request.method == "POST":

        new_url = request.POST.get("sheet_url", "").strip()
        if new_url:
            settings.google_sheet_url = new_url
            settings.save()
        sheet_url = settings.google_sheet_url

        if not sheet_url:
            return render(
                request,
                "recordings/sync_google_sheet.html",
                {
                    "settings": settings,
                    "message": "Geef eerst een Google Spreadsheet-link op."
                }
            )

        try:
            match = re.search(
                r"/spreadsheets/d/([^/]+)",
                sheet_url
            )
            if not match:
                raise ValueError(
                    "Geen geldige Google Spreadsheet-link."
                )

            spreadsheet_id = match.group(1)
            gid_match = re.search(r"gid=(\d+)", sheet_url)
            gid = gid_match.group(1) if gid_match else "0"
            csv_url = (
                f"https://docs.google.com/spreadsheets/d/"
                f"{spreadsheet_id}/export?format=csv&gid={gid}"
            )
            response = requests.get(
                csv_url,
                timeout=30
            )

            response.raise_for_status()
            reader = csv.DictReader(
                io.StringIO(response.text)
            )
            created_count = 0
            updated_count = 0
            skipped_count = 0
            for row in reader:
                video_url = (row.get("Video URL") or "").strip()
                gloss_id = (row.get("lexicon") or "").strip()
                signbank_id_raw = (row.get("GLOS NR") or "").strip()
                status = (row.get("Status") or "").strip()
                recording_by = (row.get("Wie Opname?") or "").strip()
                recording_date = (row.get("Wanneer Opname?") or "").strip()
                remarks = (row.get("Opmerkingen") or "").strip()
                if not signbank_id_raw:
                    skipped_count += 1
                    continue
                try:
                    signbank_id = int(signbank_id_raw)
                except ValueError:
                    skipped_count += 1
                    continue
                item, was_created = RecordingItem.objects.update_or_create(
                    signbank_id=signbank_id,
                    defaults={
                        "gloss_id": gloss_id,
                        "old_video_url": video_url,
                        "status": status,
                        "recording_by": recording_by,
                        "recording_date": recording_date,
                        "remarks": remarks,
                    }
                )
                if was_created:
                    created_count += 1
                else:
                    updated_count += 1

            message = (
                f"{created_count} toegevoegd, "
                f"{updated_count} bijgewerkt, "
                f"{skipped_count} overgeslagen."
            )

        except Exception as e:
            message = f"Fout bij synchroniseren: {e}"

    return render(
        request,
        "recordings/sync_google_sheet.html",
        {
            "settings": settings,
            "message": message,
        }
    )

@login_required
def recording_detail(request, signbank_id):
    item=get_object_or_404(
        RecordingItem,
        signbank_id=signbank_id
    )
    stats = RecordingItem.objects.aggregate(
                total=Count("id"),
                approved=Count(
                    "id",
                    filter=Q(status__iexact="OPGENOMEN")
                ),
                skipped=Count(
                    "id",
                    filter=Q(status__in=["OVER-OPM", "OVER-AL_VIDEO"])
                ),
            )
    total_count = stats["total"]
    approved_count = stats["approved"]
    skipped_count = stats["skipped"]
    remaining_count = total_count - approved_count - skipped_count
    progress_percentage = (
        round((approved_count / total_count) * 100)
        if total_count > 0
        else 0
    )

    return render(
        request,
        "recordings/recording_detail.html",
        {
            "item": item,
            "total_count": total_count,
            "approved_count": approved_count,
            "skipped_count": skipped_count,
            "remaining_count": remaining_count,
            "progress_percentage": progress_percentage,
        }
    )

@login_required
def go_to_next_recording_item(request):
    series = request.session.get("recording_series", [])
    index = request.session.get("recording_series_index", 0)
    next_index = index + 1
    if next_index >= len(series):
        return redirect("recording_series_complete")
    request.session["recording_series_index"] = next_index
    next_signbank_id = series[next_index]
    return redirect(
        "recording_detail",
        signbank_id=next_signbank_id,
    )

@login_required
def approve_recording(request, signbank_id):
    item = get_object_or_404(
        RecordingItem,
        signbank_id=signbank_id,
    )
    if request.method == "POST":
        item.review_status = "OPGENOMEN"
        item.save(update_fields=["review_status"])
        return go_to_next_recording_item(request)
    return redirect(
        "recording_detail",
        signbank_id=signbank_id,
    )

@login_required
def skip_recording_with_remark(request, signbank_id):
    item = get_object_or_404(
        RecordingItem,
        signbank_id=signbank_id,
    )

    if request.method == "POST":
        remark = request.POST.get("remark", "").strip()
        item.review_status = "OVER-OPM"
        item.remarks = remark
        item.save(
            update_fields=[
                "review_status",
                "remarks",
            ]
        )
        return go_to_next_recording_item(request)
    return redirect(
        "recording_detail",
        signbank_id=signbank_id,
    )

@login_required
def skip_recording_existing_video(request, signbank_id):
    item = get_object_or_404(
        RecordingItem,
        signbank_id=signbank_id,
    )

    if request.method == "POST":
        item.review_status = "OVER-AL_VIDEO"
        item.save(update_fields=["review_status"])
        return go_to_next_recording_item(request)
    return redirect(
        "recording_detail",
        signbank_id=signbank_id,
    )

@login_required
def recording_series_complete(request):
    request.session.pop("recording_series", None)
    request.session.pop("recording_series_index", None)
    return render(
        request,
        "recordings/recording_series_complete.html",
    )

@login_required
def recording_series_complete(request):
    filters = request.session.get(
        "recording_series_filters",
        {}
    )

    request.session.pop("recording_series", None)
    request.session.pop("recording_series_index", None)
    return render(
        request,
        "recordings/recording_series_complete.html",
    {
        "filters": filters,
    }
    )

@login_required
def update_review_status(request, item_id):
    if request.method == "POST":
        item = get_object_or_404(RecordingItem, id=item_id)
        review_status = request.POST.get("review_status", "")
        allowed_values = [
            "",
            "OPGENOMEN",
            "OVER-OPM",
            "OVER-AL_VIDEO",
        ]
        if review_status in allowed_values:
            item.review_status = review_status
            item.save(update_fields=["review_status"])
    return redirect(request.META.get("HTTP_REFERER", "recording_list"))