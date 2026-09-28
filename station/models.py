from django.db import models

from main.models import ServiceStation


class StationPhoto(models.Model):
    """Фотографія СТО, робочого місця або боксу."""

    photo_id = models.AutoField(primary_key=True)
    station = models.ForeignKey(
        ServiceStation,
        on_delete=models.CASCADE,
        related_name='photos',
        db_column='station_id',
    )
    photo = models.ImageField(upload_to='station_photos/')
    caption = models.CharField(max_length=200, blank=True, default='')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'station_photo'
        ordering = ['-uploaded_at']
        verbose_name = 'Фотографія СТО'
        verbose_name_plural = 'Фотографії СТО'

    def __str__(self):
        return f'Фото #{self.photo_id} — {self.station.name}'
