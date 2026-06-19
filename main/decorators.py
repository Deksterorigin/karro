from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def login_required_session(view_func):
    """
    Перевірка наявності активної сесії користувача.
    Перенаправляє на сторінку входу, якщо користувач неавторизований.
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
    Обмеження доступу до функцій за ролями користувачів.
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
