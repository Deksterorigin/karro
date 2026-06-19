# ╔══════════════════════════════════════════════════════════╗
# ║                  station/models.py                     ║
# ║   Моделі для публічної сторінки СТО                    ║
# ╚══════════════════════════════════════════════════════════╝

from django.db import models
from main.models import ServiceStation


class StationPhoto(models.Model):
    """
    Фотографія автомастерської або прикладів робіт.
    Завантажується власником СТО на публічну сторінку.
    """
    photo_id = models.AutoField(primary_key=True)
    station = models.ForeignKey(
        ServiceStation,
        on_delete=models.CASCADE,
        related_name='photos',
        db_column='station_id',
        verbose_name='СТО',
    )
    photo = models.ImageField(
        upload_to='station_photos/',
        verbose_name='Фотографія',
    )
    caption = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name='Підпис',
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата завантаження',
    )

    class Meta:
        db_table = 'station_photo'
        verbose_name = 'Фото СТО'
        verbose_name_plural = 'Фото СТО'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f'Фото #{self.photo_id} — {self.station.name}'
