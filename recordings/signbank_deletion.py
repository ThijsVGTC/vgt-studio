import logging

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from .models import SignbankEntry, SignbankUser
from .services.signbank_service import SignbankService


logger = logging.getLogger(__name__)

CONFIRMATION_SALT = "studio.signbank.delete-entry.v1"


def get_signbank_identity(user):
    identity = SignbankUser.objects.filter(
        studio_user=user,
        is_active=True,
    ).first()

    if identity is None and user.email:
        matches = list(
            SignbankUser.objects.filter(
                email__iexact=user.email,
                is_active=True,
            ).filter(
                Q(studio_user__isnull=True) | Q(studio_user=user)
            )[:2]
        )

        if len(matches) == 1:
            identity = matches[0]

    return identity


def remove_local_copy(signbank_id, expected_gloss):
    from gebarometer.models import GebarometerItem

    # Controleer eerst of de entry werkelijk uit Signbank verdwenen is.
    with SignbankService().connection() as source:
        exists = source.execute(
            "SELECT 1 FROM dictionary_gloss WHERE id = ?",
            (signbank_id,),
        ).fetchone()

        if exists:
            raise RuntimeError(
                "De entry bestaat nog in de Signbank-master."
            )

    with transaction.atomic():
        entry = (
            SignbankEntry.objects
            .select_for_update()
            .filter(signbank_id=signbank_id)
            .first()
        )

        if entry is None:
            return

        if entry.gloss != expected_gloss:
            raise RuntimeError(
                "De lokale entry is ondertussen gewijzigd."
            )

        historical = GebarometerItem.objects.filter(
            signbank_entry_id=entry.pk,
        )

        historical.filter(
            historical_gloss="",
        ).update(
            historical_gloss=entry.gloss,
        )

        historical.update(signbank_entry=None)

        # Bestaande RecordingItems blijven bewaard via SET_NULL.
        entry.delete()


@login_required
@require_http_methods(["GET", "POST"])
@csrf_protect
def delete_signbank_entry(request, signbank_id):
    if not request.user.is_staff:
        return JsonResponse(
            {
                "success": False,
                "error": "Alleen staff-gebruikers mogen entries verwijderen.",
                "canSubmit": False,
            },
            status=403,
        )

    entry = SignbankEntry.objects.filter(
        signbank_id=signbank_id,
    ).first()

    if entry is None:
        return JsonResponse(
            {
                "success": False,
                "error": "Deze entry bestaat niet meer in Studio.",
                "canSubmit": False,
            },
            status=404,
        )

    snapshot = {
        "user": request.user.pk,
        "id": entry.signbank_id,
        "gloss": entry.gloss,
    }

    token = settings.STUDIO_DELETE_API_TOKEN

    def reply(error="", status=200, can_submit=True):
        return JsonResponse(
            {
                "success": status < 400,
                "entry": {
                    "id": entry.signbank_id,
                    "gloss": entry.gloss,
                },
                "confirmationToken": signing.dumps(
                    snapshot,
                    salt=CONFIRMATION_SALT,
                ),
                "error": error,
                "canSubmit": can_submit and bool(token),
            },
            status=status,
        )

    if not token:
        return reply(
            "De verwijderkoppeling is nog niet ingesteld.",
            status=503,
            can_submit=False,
        )

    if request.method == "GET":
        return reply()

    try:
        confirmed = signing.loads(
            request.POST.get("confirmation_token", ""),
            salt=CONFIRMATION_SALT,
            max_age=600,
        )
    except signing.BadSignature:
        return reply(
            "De bevestiging is verlopen. Controleer de entry "
            "en bevestig opnieuw.",
            status=400,
        )

    if (
        confirmed != snapshot
        or request.POST.get("confirm_gloss", "") != entry.gloss
    ):
        return reply(
            "De ingevulde GLOSS komt niet overeen. "
            "Neem de GLOSS exact over.",
            status=400,
        )

    identity = get_signbank_identity(request.user)

    if identity is None:
        return reply(
            "Je account is niet eenduidig gekoppeld "
            "aan een actieve Signbank-gebruiker.",
            status=403,
        )

    api_url = (
        settings.SIGNBANK_DELETE_API_BASE_URL.rstrip("/")
        + "/"
        + str(entry.signbank_id)
    )

    try:
        response = requests.post(
            api_url,
            headers={
                "X-Studio-Delete-Token": token,
                "Accept": "application/json",
            },
            json={
                "signbank_user_id": identity.signbank_id,
                "confirm_gloss": entry.gloss,
            },
            timeout=(10, 60),
            allow_redirects=False,
        )

        result = response.json()

        if not isinstance(result, dict):
            raise ValueError("Onverwacht antwoord.")

        if (
            response.status_code != 200
            or result.get("success") is not True
        ):
            if (
                result.get("success") is False
                and 400 <= response.status_code < 500
            ):
                return reply(
                    result.get("error")
                    or "Signbank heeft de verwijdering geweigerd.",
                    status=response.status_code,
                    can_submit=response.status_code != 404,
                )

            raise ValueError("Geen eenduidige bevestiging ontvangen.")

        if (
            result.get("deleted_signbank_id") != entry.signbank_id
            or result.get("gloss") != entry.gloss
        ):
            raise ValueError(
                "De bevestiging hoort niet bij deze entry."
            )

    except (requests.RequestException, ValueError):
        logger.warning(
            "Geen eenduidige verwijderbevestiging voor Signbank-ID %s",
            entry.signbank_id,
        )

        return reply(
            "Geen eenduidige bevestiging ontvangen. "
            "Controleer eerst in Signbank of de entry nog bestaat "
            "voordat je opnieuw probeert.",
            status=502,
            can_submit=False,
        )

    deleted_id = entry.signbank_id
    deleted_gloss = entry.gloss

    try:
        remove_local_copy(deleted_id, deleted_gloss)
    except Exception:
        logger.exception(
            "Signbank-entry %s verwijderd; lokale synchronisatie "
            "nog niet afgerond",
            deleted_id,
        )

        messages.warning(
            request,
            f"{deleted_gloss} (ID {deleted_id}) is verwijderd "
            "uit Signbank. De lokale lijst wordt bij de volgende "
            "synchronisatie bijgewerkt.",
        )
    else:
        messages.success(
            request,
            f"{deleted_gloss} (ID {deleted_id}) is verwijderd "
            "uit Signbank.",
        )

    return JsonResponse({
        "success": True,
        "deleted": True,
        "redirectUrl": reverse("signbank_list"),
    })