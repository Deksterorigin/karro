import logging
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

MAX_IMAGE_SIZE_BYTES = 3 * 1024 * 1024
ALLOWED_IMAGE_FORMATS = {'JPEG', 'PNG', 'WEBP', 'GIF'}


def validate_image_upload(uploaded_file):
    """Перевіряє тип та розмір завантаженого файлу зображення."""
    if not uploaded_file:
        return False, 'Оберіть файл для завантаження.'
    if uploaded_file.size > MAX_IMAGE_SIZE_BYTES:
        return False, 'Розмір файлу перевищує 3 МБ.'

    try:
        with Image.open(uploaded_file) as image:
            if image.format not in ALLOWED_IMAGE_FORMATS:
                return False, 'Дозволені лише формати JPEG, PNG, WebP та GIF.'
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        return False, 'Файл не є коректним або пошкоджений.'
    finally:
        uploaded_file.seek(0)
    return True, None


def optimize_image(uploaded_file, max_size=(1920, 1080), quality=85):
    """Зменшує роздільну здатність великих фото перед збереженням на диск."""
    if not uploaded_file:
        return uploaded_file

    try:
        with Image.open(uploaded_file) as source:
            image_format = source.format
            if image_format == 'GIF':
                uploaded_file.seek(0)
                return uploaded_file

            image = ImageOps.exif_transpose(source)
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
            if image_format == 'JPEG' and image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')

            output = BytesIO()
            save_options = {'optimize': True}
            if image_format in ('JPEG', 'WEBP'):
                save_options['quality'] = quality
            image.save(output, format=image_format, **save_options)
        return ContentFile(output.getvalue(), name=uploaded_file.name)
    except (OSError, ValueError) as error:
        logger.warning('Не вдалося оптимізувати зображення: %s', error)
        uploaded_file.seek(0)
        return uploaded_file


def save_optimized_file(instance, field_name, uploaded_file):
    """Оптимізує зображення, зберігає його в модель та видаляє старий файл."""
    old_file = getattr(instance, field_name)
    old_name = old_file.name if old_file else None
    storage = old_file.storage

    setattr(instance, field_name, optimize_image(uploaded_file))
    instance.save(update_fields=[field_name])

    new_name = getattr(instance, field_name).name
    if old_name and old_name != new_name:
        storage.delete(old_name)


# Синоніми для зворотної сумісності
_validate_image_upload = validate_image_upload
_save_file = save_optimized_file
