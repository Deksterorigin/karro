from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def login_required_session(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Увійдіть в акаунт, щоб відкрити цю сторінку.')
            return redirect('login')
        return view_func(request, *args, **kwargs)

    return wrapper


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, 'Увійдіть в акаунт, щоб відкрити цю сторінку.')
                return redirect('login')

            if request.user.role not in roles:
                messages.error(request, 'У вас немає доступу до цієї дії.')
                return redirect('profile')

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
