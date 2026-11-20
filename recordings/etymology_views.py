import logging
import hashlib
from html.parser import HTMLParser
from urllib.parse import urlsplit, parse_qs, urlencode

import requests
from django.core.cache import cache

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST

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

class VimeoIframeParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.src = ""

    def handle_starttag(self, tag, attrs):
        if tag == "iframe" and not self.src:
            self.src = dict(attrs).get("src") or ""


@login_required
@require_GET
def vimeo_preview(request):
    original_url = request.GET.get("url", "").strip()

    try:
        parsed = urlsplit(original_url)

        if (
            not original_url
            or len(original_url) > 2000
            or parsed.scheme not in {"http", "https"}
            or parsed.hostname not in {
                "vimeo.com",
                "www.vimeo.com",
                "player.vimeo.com",
            }
            or parsed.username
            or parsed.password
            or parsed.port not in {None, 80, 443}
        ):
            raise ValueError()
    except ValueError:
        return JsonResponse(
            {
                "success": False,
                "error": "Vul een volledige, geldige Vimeo-link in.",
            },
            status=400,
        )

    cache_key = (
        "etymology-vimeo:"
        + hashlib.sha256(original_url.encode("utf-8")).hexdigest()
    )

    cached = cache.get(cache_key)

    if cached is not None:
        return JsonResponse(cached)

    try:
        response = requests.get(
            "https://vimeo.com/api/oembed.json",
            params={"url": original_url},
            timeout=(5, 15),
            allow_redirects=False,
        )

        if response.status_code in {401, 403, 404}:
            return JsonResponse(
                {
                    "success": False,
                    "error": (
                        "Vimeo kan deze video niet als voorbeeld tonen. "
                        "Controleer de volledige link en de "
                        "insluitinstellingen van de video."
                    ),
                },
                status=400,
            )

        if response.status_code != 200:
            raise ValueError()

        data = response.json()

        if not isinstance(data, dict):
            raise ValueError()

        video_id = str(data.get("video_id", ""))

        if not video_id.isascii() or not video_id.isdigit():
            raise ValueError()

        parser = VimeoIframeParser()
        parser.feed(str(data.get("html", "")))

        player = urlsplit(parser.src)

        if (
            player.scheme not in {"http", "https"}
            or player.hostname != "player.vimeo.com"
            or player.path.rstrip("/") != f"/video/{video_id}"
            or player.username
            or player.password
            or player.port not in {None, 80, 443}
        ):
            raise ValueError()

        embed_url = f"https://player.vimeo.com/video/{video_id}"
        privacy_hash = parse_qs(player.query).get("h", [""])[0]

        if privacy_hash:
            embed_url += "?" + urlencode({"h": privacy_hash})

        result = {
            "success": True,
            "videoId": video_id,
            "embedUrl": embed_url,
        }

        cache.set(cache_key, result, timeout=3600)

        return JsonResponse(result)

    except (requests.RequestException, ValueError):
        return JsonResponse(
            {
                "success": False,
                "error": (
                    "Het videovoorbeeld kon niet worden opgehaald. "
                    "Probeer het later opnieuw."
                ),
            },
            status=502,
        )