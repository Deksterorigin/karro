# ╔══════════════════════════════════════════════════════════╗
# ║                  main/decorators.py                     ║
# ║   Декоратори для захисту view-функцій                   ║
# ╚══════════════════════════════════════════════════════════╝

from functools import wraps
# pyrefly: ignore [missing-import]
from django.shortcuts import redirect
# pyrefly: ignore [missing-import]
from django.contrib import messages


def login_required_session(view_func):
    """
    Перевіряє що користувач залогінений (є user_id у сесії).
    Якщо ні — перенаправляє на сторінку входу з повідомленням.

    Використання:
        @login_required_session
        def my_view(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('user_id'):
            messages.warning(request, 'Увійдіть в акаунт, щоб отримати доступ до цієї сторінки.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def role_required(*roles):
    """
    Перевіряє що залогінений користувач має одну з вказаних ролей.
    Якщо ні — перенаправляє на профіль з повідомленням про помилку.

    Використання:
        @login_required_session
        @role_required('station')
        def station_only_view(request):
            ...

        @login_required_session
        @role_required('client', 'station')
        def any_user_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user_role = request.session.get('user_role')
            if user_role not in roles:
                messages.error(request, 'У вас немає доступу до цієї дії.')
                return redirect('profile')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
