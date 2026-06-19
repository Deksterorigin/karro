from django.contrib import admin
from .models import StationPhoto


@admin.register(StationPhoto)
class StationPhotoAdmin(admin.ModelAdmin):
    list_display = ('photo_id', 'station', 'caption', 'uploaded_at')
    list_filter = ('station',)
    search_fields = ('caption', 'station__name')
