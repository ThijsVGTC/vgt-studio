from django.conf import settings
from django.contrib.auth import get_user_model
from allauth.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.http import HttpResponseForbidden

from .models import AllowedGoogleEmail


class VGTStudioSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        if sociallogin.is_existing:
            return

        email = (sociallogin.user.email or "").strip().lower()

        if not email:
            raise ImmediateHttpResponse(
                HttpResponseForbidden("Geen e-mailadres ontvangen van Google.")
            )

        domain = email.split("@")[-1]

        allowed_domains = [
            domain_name.lower()
            for domain_name in getattr(
                settings,
                "VGT_STUDIO_GOOGLE_ALLOWED_DOMAINS",
                [],
            )
        ]

        allowed_external = AllowedGoogleEmail.objects.filter(
            email__iexact=email,
            active=True,
        ).exists()

        if domain not in allowed_domains and not allowed_external:
            raise ImmediateHttpResponse(
                HttpResponseForbidden(
                    "Dit Google-account heeft geen toegang tot VGT Studio."
                )
            )

        User = get_user_model()

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return

        sociallogin.connect(request, user)