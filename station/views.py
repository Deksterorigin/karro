import os
from django.contrib import messages
from django.db.models import Avg, Count
from django.shortcuts import render, redirect, get_object_or_404

from main.models import ServiceStation, Service, Review, Car
from main.views import get_current_user, _validate_image_upload
from .models import StationPhoto

def station_detail(request, station_id):
    """
    Публічна сторінка СТО з можливістю додавання відгуків та фото.
    """
    station = get_object_or_404(ServiceStation, pk=station_id)

    services = Service.objects.filter(station=station)
    photos = StationPhoto.objects.filter(station=station)
    reviews = Review.objects.filter(station=station).select_related('user')

    stats = Review.objects.filter(station=station).aggregate(
        avg_rating=Avg('rating'),
        review_count=Count('review_id'),
    )
    avg_rating = round(stats['avg_rating'], 1) if stats['avg_rating'] else None

    user = get_current_user(request)
    is_owner = user and user.is_station and station.user_id == user.user_id

    if request.method == 'POST':
        action = request.POST.get('action', '')

        # Додавання відгуку клієнтом
        if action == 'add_review':
            if not user:
                messages.error(request, 'Увійдіть в акаунт, щоб залишити відгук.')
            elif not user.is_client:
                messages.error(request, 'Тільки клієнти можуть залишати відгуки.')
            else:
                text = request.POST.get('review_text', '').strip()
                rating_str = request.POST.get('review_rating', '').strip()

                if not text:
                    messages.error(request, 'Введіть текст відгуку.')
                elif not rating_str.isdigit() or not (1 <= int(rating_str) <= 5):
                    messages.error(request, 'Оцінка має бути від 1 до 5.')
                else:
                    Review.objects.create(
                        text=text,
                        rating=int(rating_str),
                        user=user,
                        station=station,
                    )
                    messages.success(request, 'Дякуємо за відгук!')

        # Завантаження фото власником
        elif action == 'upload_photo':
            if not is_owner:
                messages.error(request, 'Тільки власник може завантажувати фото.')
            else:
                uploaded = request.FILES.get('station_photo')
                caption = request.POST.get('caption', '').strip()

                valid, error_msg = _validate_image_upload(uploaded)
                if not valid:
                    messages.error(request, error_msg)
                else:
                    StationPhoto.objects.create(
                        station=station,
                        photo=uploaded,
                        caption=caption,
                    )
                    messages.success(request, 'Фото завантажено.')

        # Видалення фото власником
        elif action == 'delete_photo':
            if not is_owner:
                messages.error(request, 'Тільки власник може видаляти фото.')
            else:
                photo_id = request.POST.get('photo_id', '')
                photo = StationPhoto.objects.filter(
                    photo_id=photo_id, station=station
                ).first()
                if photo:
                    try:
                        if photo.photo and os.path.isfile(photo.photo.path):
                            os.remove(photo.photo.path)
                    except (ValueError, OSError):
                        pass
                    photo.delete()
                    messages.success(request, 'Фото видалено.')
                else:
                    messages.error(request, 'Фото не знайдено.')

        return redirect('station:station_detail', station_id=station.pk)

    cars = None
    if user and user.is_client:
        cars = Car.objects.filter(user=user)

    context = {
        'station': station,
        'services': services,
        'photos': photos,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'review_count': stats['review_count'],
        'user': user,
        'is_owner': is_owner,
        'cars': cars,
    }
    return render(request, 'station/detail.html', context)
