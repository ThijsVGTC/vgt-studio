import logging

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST

from .models import SignbankEntry
from .etymology_forms import EtymologyPairForm
from .signbank_deletion import get_signbank_identity
from .services.signbank_etymology_pairs import (
    get_etymology_pairs,
    save_etymology_pair,
    delete_etymology_pair,
)
from .services.video_processing import prepare_signbank_video


logger = logging.getLogger(__name__)


@login_required
@require_GET
def etymology_pairs(request, signbank_id):
    get_object_or_404(
        SignbankEntry,
        signbank_id=signbank_id,
    )

    return JsonResponse({
        "success": True,
        "pairs": get_etymology_pairs(signbank_id),
        "canEdit": request.user.is_staff,
        "csrfToken": get_token(request),
        "saveUrl": reverse(
            "signbank_save_etymology_pair",
            kwargs={"signbank_id": signbank_id},
        ),
        "deleteUrl": reverse(
            "signbank_delete_etymology_pair",
            kwargs={"signbank_id": signbank_id},
        ),
        "vimeoPreviewUrl": reverse("signbank_vimeo_preview"),
        "maxUploadBytes": 250 * 1024 * 1024,
    })


@login_required
@require_POST
@csrf_protect
def save_etymology_pair_view(request, signbank_id):
    if not request.user.is_staff:
        return JsonResponse(
            {
                "success": False,
                "error": "Alleen staff-gebruikers mogen etymologie wijzigen.",
                "outcomeUnknown": False,
            },
            status=403,
        )

    get_object_or_404(
        SignbankEntry,
        signbank_id=signbank_id,
    )

    identity = get_signbank_identity(request.user)

    if identity is None:
        return JsonResponse(
            {
                "success": False,
                "error": (
                    "Je account is niet eenduidig gekoppeld "
                    "aan een actieve Signbank-gebruiker."
                ),
                "outcomeUnknown": False,
            },
            status=403,
        )

    form = EtymologyPairForm(request.POST, request.FILES)

    if not form.is_valid():
        return JsonResponse(
            {
                "success": False,
                "errors": form.errors.get_json_data(),
                "outcomeUnknown": False,
            },
            status=400,
        )

    data = form.cleaned_data

    arguments = {
        "signbank_id": signbank_id,
        "video_url": data.get("video_url", ""),
        "text": data["text"],
        "signbank_user_id": identity.signbank_id,
        "pair_number": data.get("pair_number"),
        "expected_revision": data.get("expected_revision") or None,
        "keep_video": data["source_type"] == "keep",
        "published": data["published"],
    }

    try:
        if data["source_type"] in {"upload", "webcam"}:
            with prepare_signbank_video(data["video"]) as prepared:
                saved = save_etymology_pair(
                    **arguments,
                    prepared_video_path=prepared,
                )
        else:
            saved = save_etymology_pair(**arguments)

    except ValidationError as exc:
        return JsonResponse(
            {
                "success": False,
                "error": " ".join(exc.messages),
                "outcomeUnknown": False,
            },
            status=400,
        )

    except ValueError as exc:
        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
                "outcomeUnknown": False,
            },
            status=400,
        )

    except Exception:
        logger.exception(
            "Etymologiepaar opslaan kon niet worden bevestigd "
            "voor Signbank-ID %s",
            signbank_id,
        )

        return JsonResponse(
            {
                "success": False,
                "error": (
                    "De opslag kon niet worden bevestigd. "
                    "Laad de etymologie opnieuw en controleer "
                    "het resultaat voordat je nogmaals opslaat."
                ),
                "outcomeUnknown": True,
            },
            status=500,
        )

    warning = ""

    try:
        call_command(
            "sync_signbank",
            signbank_id=signbank_id,
            verbosity=0,
        )
    except Exception:
        logger.exception(
            "Etymologiepaar opgeslagen; synchronisatie nog "
            "niet afgerond voor Signbank-ID %s",
            signbank_id,
        )

        warning = (
            "Het paar is opgeslagen in Signbank. "
            "Het bijwerken van de lokale lijst is nog niet afgerond."
        )

    return JsonResponse({
        "success": True,
        "pair": saved,
        "message": "Etymologiepaar opgeslagen.",
        "warning": warning,
    })

@login_required
@require_POST
@csrf_protect
def delete_etymology_pair_view(request, signbank_id):
    if not request.user.is_staff:
        return JsonResponse({
            "success": False,
            "error": "Alleen staff-gebruikers mogen etymologie verwijderen.",
            "outcomeUnknown": False,
        }, status=403)

    get_object_or_404(SignbankEntry, signbank_id=signbank_id)

    identity = get_signbank_identity(request.user)

    if identity is None:
        return JsonResponse({
            "success": False,
            "error": "Je account is niet gekoppeld aan een actieve Signbank-gebruiker.",
            "outcomeUnknown": False,
        }, status=403)

    try:
        pair_number = int(request.POST.get("pair_number", ""))
    except (ValueError, TypeError):
        return JsonResponse({
            "success": False,
            "error": "Ongeldig paarnummer.",
            "outcomeUnknown": False,
        }, status=400)

    try:
        delete_etymology_pair(
            signbank_id=signbank_id,
            pair_number=pair_number,
            expected_revision=request.POST.get("expected_revision", ""),
            signbank_user_id=identity.signbank_id,
        )
    except ValueError as exc:
        return JsonResponse({
            "success": False,
            "error": str(exc),
            "outcomeUnknown": False,
        }, status=400)
    except Exception:
        logger.exception(
            "Verwijderen etymologiepaar niet bevestigd voor Signbank-ID %s",
            signbank_id,
        )
        return JsonResponse({
            "success": False,
            "error": "Verwijdering niet bevestigd. Heropen het scherm en controleer het paar.",
            "outcomeUnknown": True,
        }, status=500)

    warning = ""

    try:
        call_command(
            "sync_signbank",
            signbank_id=signbank_id,
            verbosity=0,
        )
    except Exception:
        logger.exception(
            "Etymologiepaar verwijderd; synchronisatie mislukt voor Signbank-ID %s",
            signbank_id,
        )
        warning = "Het paar is verwijderd. De lokale lijst is nog niet bijgewerkt."

    return JsonResponse({
        "success": True,
        "pairNumber": pair_number,
        "warning": warning,
    })