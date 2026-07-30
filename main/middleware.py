from django.shortcuts import redirect
from django.contrib import messages
from .models import User


class BanCheckMiddleware:
    """
    Перевіряє, чи не заблоковано користувача.
    Якщо акаунт неактивний, здійснює вихід з системи та перенаправляє на вхід.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_active:
            from django.contrib.auth import logout
            logout(request)
            messages.error(
                request,
                "Ваш аккаунт був заблокований адміністратором."
            )
            return redirect('login')

        response = self.get_response(request)
        return response
