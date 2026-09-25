import csv
import io
import re
import requests
import gspread
import shutil

from pathlib import PurePosixPath, Path
from urllib.parse import urlparse

from django.shortcuts import get_object_or_404, render, redirect
from django.conf import settings
from .models import RecordingItem, AppSettings, SignbankEntry
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse
from .thumbnail_utils import ( generate_thumbnail_for_item,)

# Create your views here.

@login_required
def bulk_video_upload(request):
    results = []
    if request.method == "POST":
        uploaded_videos = request.FILES.getlist("videos")
        for uploaded_video in uploaded_videos:
            original_filename = uploaded_video.name
            filename = PurePosixPath(original_filename).name
            result = {
                "filename": filename,
                "status": "",
                "message": "",
                "item": None,
            }
            # Alleen MP4 toelaten
            if not filename.lower().endswith(".mp4"):
                result["status"] = "error"
                result["message"] = "Geen MP4-bestand."
                results.append(result)
                continue
            stem = PurePosixPath(filename).stem.strip()
            matched_item = None
            # -------------------------------------------------
            # 1. Alleen Signbank ID
            # Bijvoorbeeld:
            # 7270.mp4
            # -------------------------------------------------
            if stem.isdigit():
                signbank_id = int(stem)
                matched_item = (
                    RecordingItem.objects
                    .filter(signbank_id=signbank_id)
                    .first()
                )
                if not matched_item:
                    result["status"] = "error"
                    result["message"] = (
                        f"Signbank ID {signbank_id} niet gevonden."
                    )
                    results.append(result)
                    continue
            else:
                # -------------------------------------------------
                # 2. Bestandsnaam + Signbank ID
                # Bijvoorbeeld:
                # MAROKKO-D-7270.mp4
                # -------------------------------------------------
                parts = stem.rsplit("-", 1)
                if (
                    len(parts) == 2
                    and parts[1].isdigit()
                ):
                    filename_gloss = parts[0].strip()
                    signbank_id = int(parts[1])
                    item_by_id = (
                        RecordingItem.objects
                        .filter(signbank_id=signbank_id)
                        .first()
                    )
                    if item_by_id:
                        # ID bestaat, maar gloss moet ook overeenkomen
                        if (
                            item_by_id.gloss_id.strip().casefold()
                            != filename_gloss.casefold()
                        ):
                            result["status"] = "conflict"
                            result["message"] = (
                                f"ID {signbank_id} hoort bij "
                                f"{item_by_id.gloss_id}, niet bij "
                                f"{filename_gloss}."
                            )
                            results.append(result)
                            continue
                        matched_item = item_by_id
                # -------------------------------------------------
                # 3. Alleen bestandsnaam
                # Bijvoorbeeld:
                # MAROKKO-D.mp4
                # -------------------------------------------------
                if matched_item is None:
                    matches = RecordingItem.objects.filter(
                        gloss_id__iexact=stem
                    )
                    match_count = matches.count()
                    if match_count == 1:
                        matched_item = matches.first()
                    elif match_count > 1:
                        result["status"] = "conflict"
                        result["message"] = (
                            "Deze bestandsnaam komt bij meerdere "
                            "Signbank-items voor."
                        )
                        results.append(result)
                        continue
            # -------------------------------------------------
            # Geen match gevonden
            # -------------------------------------------------
            if matched_item is None:
                result["status"] = "error"
                result["message"] = (
                    "Geen overeenkomst gevonden."
                )
                results.append(result)
                continue
            # -------------------------------------------------
            # Er staat al een nieuwe video
            # -------------------------------------------------
            if matched_item.new_video:
                result["status"] = "warning"
                result["item"] = matched_item
                result["message"] = (
                    "Er is al een nieuwe video gekoppeld. "
                    "Bestand niet vervangen."
                )
                results.append(result)
                continue
            # -------------------------------------------------
            # Video opslaan bij RecordingItem
            # -------------------------------------------------
            matched_item.new_video.save(
                filename,
                uploaded_video,
                save=False,
            )
            matched_item.new_video_status = "WACHT_OP_CONTROLE"
            matched_item.save(update_fields=["new_video","new_video_status",])
            result["status"] = "success"
            result["item"] = matched_item
            result["message"] = "Video gekoppeld."
            results.append(result)
    return render(
        request,
        "recordings/bulk_video_upload.html",
        {
            "results": results,
        },
    )

@login_required
def video_review_overview(request):
    selected_status = request.GET.get(
        "status",
        ""
    ).strip()

    items = (
        RecordingItem.objects
        .filter(
            Q(new_video__isnull=False) & ~Q(new_video="")
            |
            Q(rejected_video__isnull=False) & ~Q(rejected_video="")
        )
        .order_by("-id")
    )

    if selected_status:
        items = items.filter(
            new_video_status=selected_status
        )

    waiting_count = RecordingItem.objects.filter(
        new_video_status="WACHT_OP_CONTROLE"
    ).count()

    approved_count = RecordingItem.objects.filter(
        new_video_status="GOEDGEKEURD"
    ).count()

    rejected_count = RecordingItem.objects.filter(
        new_video_status="AFGEKEURD"
    ).count()

    total_count = (
        RecordingItem.objects
        .filter(
            Q(new_video__isnull=False) & ~Q(new_video="")
            |
            Q(rejected_video__isnull=False) & ~Q(rejected_video="")
        )
        .count()
    )

    return render(
        request,
        "recordings/video_review_overview.html",
        {
            "items": items,
            "selected_status": selected_status,
            "waiting_count": waiting_count,
            "approved_count": approved_count,
            "rejected_count": rejected_count,
            "total_count": total_count,
        },
    )

@login_required
def video_review_item(
    request,
    signbank_id,
):

    item = get_object_or_404(
        RecordingItem,
        signbank_id=signbank_id,
    )

    if not item.new_video and not item.rejected_video:
        return redirect(
            "video_review_overview"
        )

    return render(
        request,
        "recordings/video_review.html",
        {
            "item": item,
            "single_item": True,
            "return_to": "overview",
        },
    )

@login_required
def video_review(request):
    items = (
        RecordingItem.objects
        .exclude(new_video="")
        .filter(new_video_status="WACHT_OP_CONTROLE")
        .order_by("id")
    )

    total_count = items.count()

    if total_count == 0:
        return render(
            request,
            "recordings/video_review.html",
            {
                "item": None,
                "total_count": 0,
                "position": 0,
            },
        )

    item = items.first()

    approved_count = RecordingItem.objects.filter(
        new_video_status="GOEDGEKEURD"
    ).count()

    rejected_count = RecordingItem.objects.filter(
        new_video_status="AFGEKEURD"
    ).count()

    return render(
        request,
        "recordings/video_review.html",
        {
            "item": item,
            "total_count": total_count,
            "position": 1,
            "approved_count": approved_count,
            "rejected_count": rejected_count,
            "single_item": False,
            "return_to": "queue",
        },
    )

@login_required
def approve_new_video(request, signbank_id):
    item = get_object_or_404(
        RecordingItem,
        signbank_id=signbank_id,
    )

    if request.method == "POST":

        item.new_video_status = "GOEDGEKEURD"

        if item.review_status == "OPNAME_AFGEKEURD":
            item.review_status = "OPGENOMEN"

        item.video_review_remarks = request.POST.get(
            "video_review_remarks",
            ""
        ).strip()

        # Eerst de statuswijzigingen opslaan
        item.save(
            update_fields=[
                "new_video_status",
                "review_status",
                "video_review_remarks",
            ]
        )

        # -------------------------------------------------
        # Oude afgekeurde video veilig verwijderen
        # -------------------------------------------------

        if item.rejected_video:

            rejected_path = Path(item.rejected_video.path)

            if rejected_path.exists():
                rejected_path.unlink()

            item.rejected_video = None

            item.save(
                update_fields=[
                    "rejected_video",
                ]
            )

    if request.POST.get("return_to") == "overview":
        return redirect("video_review_overview")

    return redirect("video_review")

@login_required
def reject_new_video(request, signbank_id):
    item = get_object_or_404(
        RecordingItem,
        signbank_id=signbank_id,
    )

    if request.method == "POST":
        item.new_video_status = "AFGEKEURD"
        item.review_status = "OPNAME_AFGEKEURD"

        item.video_review_remarks = request.POST.get(
            "video_review_remarks",
            ""
        ).strip()

        # -------------------------------------------------
        # Nieuwe video fysiek verplaatsen naar rejected
        # -------------------------------------------------

        if item.new_video:
            source_path = Path(item.new_video.path)

            rejected_dir = (
                Path(settings.MEDIA_ROOT)
                / "recordings"
                / "rejected"
            )

            rejected_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            destination_path = (
                rejected_dir
                / source_path.name
            )

            # Als er toevallig al een bestand met dezelfde naam staat,
            # gebruik Signbank ID om overschrijven te voorkomen.
            if destination_path.exists():
                destination_path = (
                    rejected_dir
                    / f"{item.signbank_id}_{source_path.name}"
                )

            shutil.move(
                str(source_path),
                str(destination_path),
            )

            item.rejected_video.name = (
                f"recordings/rejected/"
                f"{destination_path.name}"
            )

            # new_video vrijmaken zodat een nieuwe opname
            # opnieuw kan worden geüpload
            item.new_video = None

        item.save(
            update_fields=[
                "new_video_status",
                "review_status",
                "video_review_remarks",
                "rejected_video",
                "new_video",
            ]
        )

    if request.POST.get("return_to") == "overview":
        return redirect("video_review_overview")

    return redirect("video_review")

@login_required
def reopen_rejected_video(request, signbank_id):

    item = get_object_or_404(
        RecordingItem,
        signbank_id=signbank_id,
    )

    if request.method == "POST":

        if item.rejected_video:

            source_path = Path(item.rejected_video.path)

            new_dir = (
                Path(settings.MEDIA_ROOT)
                / "recordings"
                / "new"
            )

            new_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            destination_path = (
                new_dir
                / source_path.name
            )

            if destination_path.exists():
                destination_path = (
                    new_dir
                    / f"{item.signbank_id}_{source_path.name}"
                )

            shutil.move(
                str(source_path),
                str(destination_path),
            )

            item.new_video.name = (
                f"recordings/new/"
                f"{destination_path.name}"
            )

            item.rejected_video = None

        item.new_video_status = "WACHT_OP_CONTROLE"

        # De opname moet niet langer als afgekeurd staan
        if item.review_status == "OPNAME_AFGEKEURD":
            item.review_status = ""

        item.save(
            update_fields=[
                "new_video",
                "rejected_video",
                "new_video_status",
                "review_status",
            ]
        )

    return redirect("video_review_overview")

@login_required
def signbank_export_preview(request):
    selected_tab = request.GET.get(
        "tab",
        "pending",
    )

    if selected_tab not in ["pending", "processed"]:
        selected_tab = "pending"

    items = (
        RecordingItem.objects
        .filter(new_video_status="GOEDGEKEURD",signbank_exported=False,)
        .exclude(new_video="")
        .order_by("-id")
    )

    export_items = []

    signbank_root = Path(
        settings.SIGNBANK_GLOSSVIDEO_ROOT
    )
    
    for item in items:

        gloss = (item.gloss_id or "").strip()

        if len(gloss) < 2:
            export_items.append({
                "item": item,
                "valid": False,
                "error": "Gloss ID is ongeldig.",
            })
            continue

        folder_name = gloss[:2].upper()

        filename = (
            f"{gloss}-{item.signbank_id}.mp4"
        )

        relative_path = (
            Path(folder_name)
            / filename
        )

        target_path = (
            signbank_root
            / relative_path
        )

        export_items.append({
            "item": item,
            "valid": True,
            "folder": folder_name,
            "filename": filename,
            "relative_path": str(relative_path),
            "target_path": str(target_path),
            "exists": target_path.exists(),
        })

    exported_items = (
        RecordingItem.objects
        .filter(signbank_exported=True)
        .order_by("-signbank_exported_at")
    )
    
    pending_count = (
        RecordingItem.objects
        .filter(
            new_video_status="GOEDGEKEURD",
            signbank_exported=False,
        )
        .exclude(new_video="")
        .count()
    )

    processed_count = (
        RecordingItem.objects
        .filter(signbank_exported=True)
        .count()
        )
    return render(
        request,
        "recordings/signbank_export_preview.html",
        {
            "export_items": export_items,
            "exported_items": exported_items,
            "selected_tab": selected_tab,
            "pending_count": pending_count,
            "processed_count": processed_count,
        },
    )

@login_required
def signbank_export_item(request, signbank_id):

    item = get_object_or_404(
        RecordingItem,
        signbank_id=signbank_id,
    )

    if request.method != "POST":
        return redirect("signbank_export_preview")

    # Alleen goedgekeurde video's verwerken
    if item.new_video_status != "GOEDGEKEURD":
        messages.error(
            request,
            "Deze video is niet goedgekeurd."
        )
        return redirect("signbank_export_preview")

    if not item.new_video:
        messages.error(
            request,
            "Er is geen nieuwe video beschikbaar."
        )
        return redirect("signbank_export_preview")

    gloss = (item.gloss_id or "").strip()

    if len(gloss) < 2:
        messages.error(
            request,
            "Ongeldige gloss ID."
        )
        return redirect("signbank_export_preview")

    signbank_root = Path(
        settings.SIGNBANK_GLOSSVIDEO_ROOT
    )

    folder_name = gloss[:2].upper()

    target_dir = (
        signbank_root
        / folder_name
    )

    target_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    filename = (
        f"{gloss}-{item.signbank_id}.mp4"
    )

    source_path = Path(
        item.new_video.path
    )

    target_path = (
        target_dir
        / filename
    )

    # Extra veiligheid
    if not source_path.exists():
        messages.error(
            request,
            "Het bronbestand bestaat niet meer."
        )
        return redirect(f"{reverse('signbank_export_preview')}?tab=pending")

    try:

        # -------------------------------------------------
        # Bestaande Signbank-video vervangen
        # -------------------------------------------------

        if target_path.exists():
            target_path.unlink()

        # -------------------------------------------------
        # Nieuwe video naar Signbank verplaatsen
        # -------------------------------------------------

        shutil.move(
            str(source_path),
            str(target_path),
        )

        thumbnail_success, thumbnail_message = (
            generate_thumbnail_for_item(
                item,
                source_path=target_path,
                force=True,
            )
        )

        # -------------------------------------------------
        # Database pas aanpassen nadat verplaatsen gelukt is
        # -------------------------------------------------

        item.new_video = None
        item.signbank_exported = True
        item.signbank_exported_at = timezone.now()

        item.save(
            update_fields=[
                "new_video",
                "signbank_exported",
                "signbank_exported_at",
            ]
        )

        messages.success(
            request,
            f"{gloss} is naar Signbank verwerkt."
        )

        if not thumbnail_success:
            messages.warning(
                request,
                "Video is naar Signbank verwerkt, "
                f"maar thumbnail maken is mislukt: "
                f"{thumbnail_message}"
            )


    except Exception as exc:

        messages.error(
            request,
            f"Export naar Signbank mislukt: {exc}"
        )

    return redirect(
        "signbank_export_preview"
    )

@login_required
def signbank_export_bulk(request):

    if request.method != "POST":
        return redirect(
            f"{reverse('signbank_export_preview')}?tab=pending"
        )

    selected_ids = request.POST.getlist("selected_items")

    if not selected_ids:
        messages.warning(
            request,
            "Geen video's geselecteerd."
        )
        return redirect(
            f"{reverse('signbank_export_preview')}?tab=pending"
        )

    items = (
        RecordingItem.objects
        .filter(
            signbank_id__in=selected_ids,
            new_video_status="GOEDGEKEURD",
            signbank_exported=False,
        )
        .exclude(new_video="")
    )

    success_count = 0
    error_count = 0
    thumbnail_error_count = 0

    signbank_root = Path(
        settings.SIGNBANK_GLOSSVIDEO_ROOT
    )

    for item in items:

        gloss = (item.gloss_id or "").strip()

        if len(gloss) < 2 or not item.new_video:
            error_count += 1
            continue

        source_path = Path(
            item.new_video.path
        )

        if not source_path.exists():
            error_count += 1
            continue

        folder_name = gloss[:2].upper()

        target_dir = (
            signbank_root
            / folder_name
        )

        filename = (
            f"{gloss}-{item.signbank_id}.mp4"
        )

        target_path = (
            target_dir
            / filename
        )

        try:

            target_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            if target_path.exists():
                target_path.unlink()

            shutil.move(
                str(source_path),
                str(target_path),
            )

            thumbnail_success, _ = (
                generate_thumbnail_for_item(
                    item,
                    source_path=target_path,
                    force=True,
                )
            )

            if not thumbnail_success:
                thumbnail_error_count += 1

            item.new_video = None
            item.signbank_exported = True
            item.signbank_exported_at = timezone.now()

            item.save(
                update_fields=[
                    "new_video",
                    "signbank_exported",
                    "signbank_exported_at",
                ]
            )

            success_count += 1

        except Exception:
            error_count += 1

    if success_count:
        messages.success(
            request,
            f"{success_count} video('s) naar Signbank verwerkt."
        )

    if error_count:
        messages.warning(
            request,
            f"{error_count} video('s) konden niet worden verwerkt."
        )

    if thumbnail_error_count:
        messages.warning(
            request,
            f"{thumbnail_error_count} thumbnail(s) "
            "konden niet automatisch worden vernieuwd."
        )

    return redirect(
        f"{reverse('signbank_export_preview')}?tab=pending"
    )

@login_required
def signbank_list(request):
    entries = SignbankEntry.objects.all()

    search_query = request.GET.get("q", "").strip()
    selected_category = request.GET.get("category", "").strip()
    selected_label = request.GET.get("label", "").strip()
    selected_in_dictionary = request.GET.get("in_dictionary", "").strip()

    # -------------------------------------------------
    # Zoeken
    # -------------------------------------------------
    if search_query:
        search_filter = (
            Q(gloss__icontains=search_query)
            | Q(mogelijke_vertaling__icontains=search_query)
            | Q(labels__icontains=search_query)
        )

        if search_query.isdigit():
            search_filter |= Q(signbank_id=int(search_query))

        entries = entries.filter(search_filter)

    # -------------------------------------------------
    # Categorie
    # Een categorie kan in een van de 5 velden staan.
    # -------------------------------------------------
    if selected_category:
        entries = entries.filter(
            Q(categorie_1=selected_category)
            | Q(categorie_2=selected_category)
            | Q(categorie_3=selected_category)
            | Q(categorie_4=selected_category)
            | Q(categorie_5=selected_category)
        )

    # -------------------------------------------------
    # Label
    # -------------------------------------------------
    if selected_label:
        entries = entries.filter(
            labels__icontains=selected_label
        )

    # -------------------------------------------------
    # In woordenboek
    # -------------------------------------------------
    if selected_in_dictionary == "yes":
        entries = entries.filter(
            in_woordenboek=True
        )
    elif selected_in_dictionary == "no":
        entries = entries.filter(
            in_woordenboek=False
        )

    entries = entries.order_by("gloss", "signbank_id")

    # -------------------------------------------------
    # Alle beschikbare categorieën verzamelen
    # -------------------------------------------------
    categories = set()

    for field_name in [
        "categorie_1",
        "categorie_2",
        "categorie_3",
        "categorie_4",
        "categorie_5",
    ]:
        values = (
            SignbankEntry.objects
            .exclude(**{field_name: ""})
            .values_list(field_name, flat=True)
        )

        categories.update(
            value
            for value in values
            if value
        )

    categories = sorted(
        categories,
        key=str.casefold,
    )

    # -------------------------------------------------
    # Alle labels verzamelen
    # labels zijn opgeslagen als:
    # "label 1; label 2; label 3"
    # -------------------------------------------------
    labels = set()

    for label_string in (
        SignbankEntry.objects
        .exclude(labels="")
        .values_list("labels", flat=True)
    ):
        if not label_string:
            continue

        for label in label_string.split(";"):
            label = label.strip()

            if label:
                labels.add(label)

    labels = sorted(
        labels,
        key=str.casefold,
    )

    # -------------------------------------------------
    # Paginering
    # -------------------------------------------------
    paginator = Paginator(entries, 50)

    page_number = request.GET.get(
        "page",
        1,
    )

    page_obj = paginator.get_page(
        page_number
    )

    return render(
        request,
        "recordings/signbank_list.html",
        {
            "entries": page_obj,
            "page_obj": page_obj,

            "search_query": search_query,

            "categories": categories,
            "selected_category": selected_category,

            "labels": labels,
            "selected_label": selected_label,

            "selected_in_dictionary": selected_in_dictionary,

            "filtered_count": paginator.count,
        },
    )

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
            | Q(video_review_remarks__icontains=search_query)
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
            "OPNAME_AFGEKEURD",
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
            thumbnail_count = 0
            thumbnail_error_count = 0
            thumbnail_errors = []

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

                    if item.old_video_url:

                        success, thumbnail_message = (
                            generate_thumbnail_for_item(
                                item,
                                force=True,
                            )
                        )

                        if success:

                            thumbnail_count += 1

                        else:

                            thumbnail_error_count += 1
                            thumbnail_errors.append(
                                f"{item.signbank_id} ({item.gloss_id}): "
                                f"{thumbnail_message}"
                            )

                            print(
                                f"Thumbnail fout voor "
                                f"{item.signbank_id} "
                                f"({item.gloss_id}): "
                                f"{thumbnail_message}"
                            )

                else:

                    updated_count += 1
            message = (
                f"{created_count} toegevoegd, "
                f"{updated_count} bijgewerkt, "
                f"{skipped_count} overgeslagen. "
                f"{thumbnail_count} nieuwe thumbnails gemaakt."
            )

            if thumbnail_error_count:
                message += (
                    f" {thumbnail_error_count} thumbnails "
                    f"konden niet gemaakt worden."
                )

                if thumbnail_errors:
                    message += (
                        " Eerste fout: "
                        + thumbnail_errors[0]
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

        gid_match = re.search(
            r"gid=(\d+)",
            sheet_url
        )

        gid = int(
            gid_match.group(1)
        ) if gid_match else 0

        worksheet = None

        for ws in spreadsheet.worksheets():

            if ws.id == gid:
                worksheet = ws
                break

        if worksheet is None:
            worksheet = spreadsheet.sheet1

        rows = worksheet.get_all_values()

        if not rows:
            raise ValueError(
                "De Google Sheet is leeg."
            )

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
                raise ValueError(
                    f"Kolom '{header}' ontbreekt in Google Sheet."
                )

        column_map = {
            header: headers.index(header) + 1
            for header in required_headers
        }

        items = {
            str(item.signbank_id): item
            for item in RecordingItem.objects.all()
        }

        updated_count = 0
        skipped_count = 0

        updates = []

        for row_number, row in enumerate(
            rows[1:],
            start=2,
        ):

            glos_index = (
                column_map["GLOS NR"] - 1
            )

            if len(row) <= glos_index:
                skipped_count += 1
                continue

            glos_nr = (
                row[glos_index].strip()
            )

            if not glos_nr:
                skipped_count += 1
                continue

            item = items.get(glos_nr)

            if not item:
                skipped_count += 1
                continue

            values = {
                "Status": item.status or "",
                "Wie Opname?": item.recording_by or "",
                "Wanneer Opname?": (
                    str(item.recording_date)
                    if item.recording_date
                    else ""
                ),
                "Opmerkingen": item.remarks or "",
                "Opnamestatus": item.review_status or "",
            }

            for header, value in values.items():

                column_number = column_map[header]

                cell = gspread.utils.rowcol_to_a1(
                    row_number,
                    column_number,
                )

                updates.append({
                    "range": cell,
                    "values": [[value]],
                })

            updated_count += 1

        if updates:

            worksheet.batch_update(
                updates
            )

        message = (
            f"{updated_count} rijen terug gesynchroniseerd "
            f"naar Google Sheet. "
            f"{skipped_count} rijen overgeslagen."
        )

    except Exception as e:

        message = (
            f"Fout bij terug synchroniseren: {e}"
        )

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
def update_video_source(request,signbank_id,):
    item = get_object_or_404(
        RecordingItem,
        signbank_id=signbank_id,
    )

    if request.method == "POST":
        gloss_id = request.POST.get(
            "gloss_id",
            ""
        ).strip()

        old_video_url = request.POST.get(
            "old_video_url",
            ""
        ).strip()

        if not gloss_id:
            messages.error(
                request,
                "Gloss mag niet leeg zijn."
            )

            return redirect(
                "recording_detail",
                signbank_id=signbank_id,
            )

        if not old_video_url:
            messages.error(
                request,
                "Oude video-URL mag niet leeg zijn."
            )

            return redirect(
                "recording_detail",
                signbank_id=signbank_id,
            )

        item.gloss_id = gloss_id
        item.old_video_url = old_video_url

        item.save(
            update_fields=[
                "gloss_id",
                "old_video_url",
            ]
        )

        # Thumbnail ALTIJD opnieuw maken na
        # wijziging van gloss/video-URL
        success, thumbnail_message = (
            generate_thumbnail_for_item(
                item,
                force=True,
            )
        )

        if success:
            messages.success(
                request,
                "Gloss en video-URL aangepast. "
                "Thumbnail is opnieuw gegenereerd."
            )

        else:
            messages.warning(
                request,
                "Gloss en video-URL zijn aangepast, "
                "maar de thumbnail kon niet "
                f"gegenereerd worden: "
                f"{thumbnail_message}"
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