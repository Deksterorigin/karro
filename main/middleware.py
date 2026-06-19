from django.shortcuts import redirect
from django.contrib import messages
from .models import User

class BanCheckMiddleware:
    """
    Перевірка активності авторизованого користувача.
    Якщо акаунт заблоковано (is_active=False), сесія очищається,
    а користувача перенаправляє на сторінку входу.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user_id = request.session.get('user_id')
        if user_id:
            try:
                user = User.objects.only('is_active').get(pk=user_id)
                if not user.is_active:
                    request.session.flush()
                    messages.error(request, "Ваш аккаунт був заблокований адміністратором.")
                    return redirect('login')
            except User.DoesNotExist:
                request.session.flush()
                return redirect('login')

        response = self.get_response(request)
        return response
