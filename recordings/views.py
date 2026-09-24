import csv
import io
import re
import requests
import gspread

from pathlib import PurePosixPath
from urllib.parse import urlparse

from django.shortcuts import get_object_or_404, render, redirect
from django.conf import settings
from .models import RecordingItem, AppSettings
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.core.paginator import Paginator

# Create your views here.

@login_required
def recording_list(request):
    items = RecordingItem.objects.all()
    selected_status = request.GET.get("status", "")
    selected_recording_by = request.GET.get("recording_by", "")
    selected_recording_date = request.GET.get("recording_date", "")
    selected_review_status = request.GET.get("review_status", "")
    search_query = request.GET.get("q", "").strip()
    sort = request.GET.get("sort","")
    direction = request.GET.get("direction","")
    allowed_sorts = {
        "gloss_id": "gloss_id",
        "signbank_id": "signbank_id",
        "recording_date": "recording_date",
    }

    if selected_status:
        items=items.filter(status=selected_status)
    if selected_recording_by:
        items = items.filter(recording_by=selected_recording_by)
    if selected_recording_date:
        items = items.filter(recording_date=selected_recording_date)
    if selected_review_status:
        items = items.filter(review_status=selected_review_status)
    if search_query:
        search_filter = (
            Q(gloss_id__icontains=search_query)
            | Q(status__icontains=search_query)
            | Q(recording_by__icontains=search_query)
            | Q(recording_date__icontains=search_query)
            | Q(remarks__icontains=search_query)
            | Q(review_status__icontains=search_query)
        )
        if search_query.isdigit():
            search_filter |= Q(signbank_id=int(search_query))
        items = items.filter(search_filter)

    if sort in allowed_sorts:
        order_field = allowed_sorts[sort]
        if direction == "desc":
            order_field = f"-{order_field}"
        items = items.order_by(order_field)
    else:
        items = items.order_by("-id")

    filtered_ids = list(
        items.values_list("signbank_id", flat=True)
    )
    # Alle database-ID's van de volledige gefilterde lijst.
    # Nodig zodat "alles selecteren" ook niet-geladen rijen selecteert.

    filtered_item_ids = list(
        items.values_list("id", flat=True)
        )
    filtered_item_ids_csv = ",".join(
        str(item_id) for item_id in filtered_item_ids
        )
    filtered_count = len(filtered_item_ids)
    paginator = Paginator(items, 25)
    page_number = request.GET.get("page",1)
    page_obj = paginator.get_page(page_number)
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
            "items": page_obj,
            "page_obj": page_obj,
            "statuses": statuses,
            "recording_people": recording_people,
            "recording_dates": recording_dates,
            "selected_status": selected_status,
            "selected_recording_by": selected_recording_by,
            "selected_recording_date": selected_recording_date,
            "selected_review_status": selected_review_status,
            "search_query": search_query,
            "sort": sort,
            "direction": direction,
            "filtered_ids": filtered_ids,
            "filtered_item_ids_csv": filtered_item_ids_csv,
            "filtered_count": filtered_count,
        }
    )

@login_required
def bulk_update_recordings(request):
    if request.method != "POST":
        return redirect("recording_list")
    select_all = request.POST.get("select_all") == "1"

    if select_all:
        all_item_ids = request.POST.get(
            "all_item_ids",
            ""
        )
        items_ids = [
            item_id.strip()
            for item_id in all_item_ids.split(",")
            if item_id.strip().isdigit()
        ]
    else:
        items_ids = request.POST.getlist(
            "item_ids"
        )
    if not items_ids:
        return redirect("recording_list")
    items=RecordingItem.objects.filter(id__in=items_ids)
    recording_by = request.POST.get("bulk_recording_by","__KEEP__")
    recording_date = request.POST.get("bulk_recording_date","__KEEP__")
    new_recording_by = request.POST.get("bulk_recording_by_new","").strip()
    new_recording_date = request.POST.get("bulk_recording_date_new","").strip()
    status = request.POST.get("bulk_status", "__KEEP__")
    review_status = request.POST.get("bulk_review_status", "__KEEP__")

    # Wie opname
    if recording_by == "__NEW":
        if new_recording_by:
            items.update(recording_by=new_recording_by)
    elif recording_by != "__KEEP__":
        if recording_by == "__EMPTY__":
            recording_by = ""
        items.update(
            recording_by=recording_by
        )

    # Wanneer opname
    if recording_date == "__NEW__":
        if new_recording_date:
            items.update(recording_date=new_recording_date)
    elif recording_date != "__KEEP__":
        if recording_date == "__EMPTY__":
            recording_date = ""
        items.update(
            recording_date=recording_date
        )

    # Status
    if status != "__KEEP__":
        if status == "__EMPTY__":
            status = ""
        items.update(
            status=status
        )

    # Opnamestatus
    if review_status != "__KEEP__":
        allowed_review_statuses = [
            "",
            "OPGENOMEN",
            "OVER-OPM",
            "OVER-AL_VIDEO",
        ]
        if review_status == "__EMPTY__":
            review_status = ""
        if review_status in allowed_review_statuses:
            items.update(
                review_status=review_status
            )

    return redirect("recording_list")


@login_required
def start_recording_series(request):

    if request.method != "POST":
        return redirect("recording_list")
    signbank_ids = request.POST.getlist("signbank_ids")
    if not signbank_ids:
        request.session["opnamereeks_actief"] = False
        return redirect("recording_list")
    
    signbank_ids = [int(signbank_id) for signbank_id in signbank_ids]
    request.session["recording_series"] = signbank_ids
    request.session["recording_series_index"] = 0
    request.session["recording_series_filters"]={
        "status": request.POST.get("status", ""),
        "recording_by": request.POST.get("recording_by", ""),
        "recording_date": request.POST.get("recording_date", ""),
        "review_status": request.POST.get("review_status", ""),
        "q": request.POST.get("q", ""),
    }
    request.session["opnamereeks_actief"] = True
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
def sync_to_google_sheet(request):
    settings_obj, created = AppSettings.objects.get_or_create(pk=1)
    if request.method != "POST":
        return redirect("sync_google_sheet")
    sheet_url = settings_obj.google_sheet_url
    if not sheet_url:
        return render(
            request,
            "recordings/sync_google_sheet.html",
            {
                "settings": settings_obj,
                "message": "Er is geen Google Spreadsheet gekoppeld.",
            },
        )
    try:
        gc = gspread.service_account(
            filename=settings.GOOGLE_SERVICE_ACCOUNT_FILE
        )
        spreadsheet = gc.open_by_url(sheet_url)
        gid_match = re.search(r"gid=(\d+)", sheet_url)
        gid = int(gid_match.group(1)) if gid_match else 0
        worksheet = None
        for ws in spreadsheet.worksheets():
            if ws.id == gid:
                worksheet = ws
                break
        if worksheet is None:
            worksheet = spreadsheet.sheet1
        rows = worksheet.get_all_values()
        if not rows:
            raise ValueError("De Google Sheet is leeg.")
        headers = rows[0]
        required_headers = [
            "GLOS NR",
            "Status",
            "Wie Opname?",
            "Wanneer Opname?",
            "Opmerkingen",
            "Opnamestatus",
        ]
        for header in required_headers:
            if header not in headers:
                headers.append(header)
        worksheet.update(
            range_name="A1",
            values=[headers],
        )
        column_map = {
            header: headers.index(header)
            for header in required_headers
        }
        items = {
            str(item.signbank_id): item
            for item in RecordingItem.objects.all()
        }
        updated_count = 0
        skipped_count = 0
        output_rows = [headers]
        for row in rows[1:]:
            while len(row) < len(headers):
                row.append("")
            glos_nr = row[
                column_map["GLOS NR"]
            ].strip()
            if not glos_nr:
                output_rows.append(row)
                skipped_count += 1
                continue
            item = items.get(glos_nr)
            if not item:
                output_rows.append(row)
                skipped_count += 1
                continue
            row[column_map["Status"]] = item.status or ""
            row[column_map["Wie Opname?"]] = item.recording_by or ""
            row[column_map["Wanneer Opname?"]] = (
                str(item.recording_date)
                if item.recording_date
                else ""
            )
            row[column_map["Opmerkingen"]] = item.remarks or ""
            row[column_map["Opnamestatus"]] = item.review_status or ""
            output_rows.append(row)
            updated_count += 1
        worksheet.update(
            range_name="A1",
            values=output_rows,
        )
        message = (
            f"{updated_count} rijen terug gesynchroniseerd "
            f"naar Google Sheet. "
            f"{skipped_count} rijen overgeslagen."
        )
    except Exception as e:
        message = f"Fout bij terug synchroniseren: {e}"
    return render(
        request,
        "recordings/sync_google_sheet.html",
        {
            "settings": settings_obj,
            "message": message,
        },
    )

@login_required
def recording_detail(request, signbank_id):
    item = get_object_or_404(
        RecordingItem,
        signbank_id=signbank_id
    )

    opnamereeks_actief = request.session.get(
        "opnamereeks_actief",
        False
    )
    has_previous_recording = False
    if opnamereeks_actief:
        series = request.session.get(
            "recording_series",
            []
        )
        if signbank_id in series:
            current_index = series.index(signbank_id)
            request.session[
                "recording_series_index"
            ] = current_index
            has_previous_recording = current_index > 0

    total_count = 0
    approved_count = 0
    skipped_count = 0
    remaining_count = 0
    progress_percentage = 0

    if opnamereeks_actief:
        # Alleen de items van de huidige opnamereeks
        series = request.session.get(
            "recording_series",
            []
        )
        reeks = RecordingItem.objects.filter(
            signbank_id__in=series
        )
        total_count = reeks.count()
        approved_count = reeks.filter(
            review_status="OPGENOMEN"
        ).count()
        skipped_count = reeks.filter(
            review_status__in=[
                "OVER-OPM",
                "OVER-AL_VIDEO",
            ]
        ).count()
        remaining_count = (
            total_count
            - approved_count
            - skipped_count
        )
        if total_count > 0:
            progress_percentage = round(
                (approved_count / total_count) * 100
            )

    return render(
        request,
        "recordings/recording_detail.html",
        {
            "item": item,
            "opnamereeks_actief": opnamereeks_actief,
            "has_previous_recording": has_previous_recording,
            "total_count": total_count,
            "approved_count": approved_count,
            "skipped_count": skipped_count,
            "remaining_count": remaining_count,
            "progress_percentage": progress_percentage,
        }
    )

@login_required
def update_remarks(request, signbank_id):
    item=get_object_or_404(
        RecordingItem,
        signbank_id=signbank_id,
    )

    if request.method == "POST":
        item.remarks = request.POST.get(
            "remarks",
            ""
        ).strip()

        item.save(
            update_fields=["remarks"]
        )
    return redirect(
        "recording_detail",
        signbank_id=signbank_id,
    )

@login_required
def stop_opnamereeks(request):
    request.session["opnamereeks_actief"] = False
    request.session.pop("recording_series", None)
    request.session.pop("recording_series_index", None)
    request.session.pop("recording_series_filters", None)
    return redirect("recording_list")

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
def go_to_previous_recording_item(request):
    series = request.session.get("recording_series",[])
    index = request.session.get("recording_series_index", 0)
    if not series:
        return redirect("recording_list")
    previous_index = index - 1
    if previous_index < 0:
        previous_index = 0
    request.session["recording_series_index"]= previous_index
    previous_signbank_id = series[previous_index]
    return redirect(
        "recording_detail",
        signbank_id=previous_signbank_id,
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
        if remark:
            if item.remark.strip():
                item.remarks = f"{item.remarks.rstrip()}\n{remark}"
            else:
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
    filters = request.session.get(
        "recording_series_filters",
        {}
    )
    request.session["opnamereeks_actief"] = False
    request.session.pop("recording_series", None)
    request.session.pop("recording_series_index", None)
    request.session.pop("recording_series_filters", None)

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