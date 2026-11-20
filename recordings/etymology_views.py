import logging

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from .models import SignbankEntry
from .signbank_deletion import get_signbank_identity
from .services.signbank_service import SignbankService
from .services.signbank_etymology import (
    save_etymology_note,
    delete_etymology_note,
)


logger = logging.getLogger(__name__)


def get_etymology_notes(signbank_id):
    result = {"video": [], "tekst": []}

    with SignbankService().connection() as conn:
        rows = conn.execute(
            """
            SELECT id, role, text
            FROM dictionary_definition
            WHERE gloss_id = ?
              AND LOWER(role) IN ('ety', 'etymology_text')
              AND text IS NOT NULL
              AND TRIM(text) != ''
            ORDER BY count ASC, id ASC
            """,
            (signbank_id,),
        ).fetchall()

    for row in rows:
        note_type = (
            "video"
            if row["role"].lower() == "ety"
            else "tekst"
        )

        result[note_type].append({
            "id": row["id"],
            "text": row["text"],
        })

    return result


def reply(success, text, level="success", status=200):
    return JsonResponse(
        {
            "success": success,
            "messages": [
                {
                    "level": level,
                    "message": text,
                }
            ],
        },
        status=status,
    )


def change_etymology(
    request,
    signbank_id,
    note_type,
    note_id=None,
    deleting=False,
):
    if not request.user.is_staff:
        return reply(
            False,
            "Alleen staff-gebruikers mogen etymologie wijzigen.",
            level="error",
            status=403,
        )

    get_object_or_404(
        SignbankEntry,
        signbank_id=signbank_id,
    )

    identity = get_signbank_identity(request.user)

    if identity is None:
        return reply(
            False,
            "Je account is niet eenduidig gekoppeld "
            "aan een actieve Signbank-gebruiker.",
            level="error",
            status=403,
        )

    try:
        if deleting:
            delete_etymology_note(
                signbank_id=signbank_id,
                note_type=note_type,
                note_id=note_id,
                signbank_user_id=identity.signbank_id,
            )
        else:
            save_etymology_note(
                signbank_id=signbank_id,
                note_type=note_type,
                text=request.POST.get("text", ""),
                note_id=note_id,
                signbank_user_id=identity.signbank_id,
            )

    except ValidationError:
        return reply(
            False,
            "Vul een geldige videolink in, beginnend met "
            "https:// of http://.",
            level="error",
            status=400,
        )

    except ValueError as exc:
        return reply(
            False,
            str(exc),
            level="error",
            status=400,
        )

    except Exception:
        logger.exception(
            "Etymologie wijzigen mislukt voor Signbank-ID %s",
            signbank_id,
        )

        return reply(
            False,
            "De wijziging kon niet worden bevestigd. "
            "Laad de gegevens opnieuw voordat je nogmaals opslaat.",
            level="error",
            status=500,
        )

    try:
        call_command(
            "sync_signbank",
            signbank_id=signbank_id,
            verbosity=0,
        )
    except Exception:
        logger.exception(
            "Etymologie opgeslagen, synchronisatie nog niet afgerond "
            "voor Signbank-ID %s",
            signbank_id,
        )

        return reply(
            True,
            "Opgeslagen in Signbank. Het bijwerken van de lokale "
            "lijst is nog niet afgerond.",
            level="warning",
        )

    return reply(
        True,
        "Etymologie verwijderd." if deleting else "Etymologie opgeslagen.",
    )


@login_required
@require_POST
@csrf_protect
def save_etymology(request, signbank_id, note_type, note_id=None):
    return change_etymology(
        request,
        signbank_id,
        note_type,
        note_id=note_id,
    )


@login_required
@require_POST
@csrf_protect
def delete_etymology(request, signbank_id, note_type, note_id):
    return change_etymology(
        request,
        signbank_id,
        note_type,
        note_id=note_id,
        deleting=True,
    )