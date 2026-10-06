from django.shortcuts import redirect
from django.urls import reverse


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        public_paths = (
            "/accounts/",
            "/logged-out/",
            "/admin/",
        )

        if (
            not request.user.is_authenticated
            and not request.path.startswith(public_paths)
        ):
            login_url = reverse("account_login")
            return redirect(f"{login_url}?next={request.get_full_path()}")

        return self.get_response(request)