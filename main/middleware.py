import time
from django.shortcuts import redirect
from django.contrib import messages
from .models import User


class BanCheckMiddleware:
    """
    Перевірка активності авторизованого користувача.
    Якщо акаунт заблоковано (is_active=False), сесія очищується,
    а користувача перенаправляє на сторінку входу.

    FIX (ARCH-05): Кешування результату перевірки у сесії з TTL
    для уникнення SQL-запиту на кожен HTTP-запит.
    """
    BAN_CHECK_TTL = 60  # Перевірка раз на хвилину

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user_id = request.session.get('user_id')
        if user_id:
            last_check = request.session.get('_ban_check_ts', 0)
            now = time.time()

            # Виконуємо запит до БД лише якщо минув TTL
            if now - last_check > self.BAN_CHECK_TTL:
                try:
                    user = User.objects.only('is_active').get(pk=user_id)
                    if not user.is_active:
                        request.session.flush()
                        messages.error(
                            request,
                            "Ваш аккаунт був заблокований адміністратором."
                        )
                        return redirect('login')
                    # Оновлюємо timestamp перевірки
                    request.session['_ban_check_ts'] = now
                except User.DoesNotExist:
                    request.session.flush()
                    return redirect('login')

        response = self.get_response(request)
        return response
