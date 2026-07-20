from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def login_required_session(view_func):
    """
    Декоратор для перевірки авторизації.
    Якщо користувач не авторизований, перенаправляє на сторінку входу.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Увійдіть в акаунт, щоб отримати доступ до цієї сторінки.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper

def role_required(*roles):
    """
    Декоратор для обмеження доступу за ролями користувача.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated or request.user.role not in roles:
                messages.error(request, 'У вас немає доступу до цієї дії.')
                return redirect('profile')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
