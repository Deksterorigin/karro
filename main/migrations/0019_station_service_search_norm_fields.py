from django.db import migrations, models

import main.textnorm


def backfill_norm_fields(apps, schema_editor):
    ServiceStation = apps.get_model('main', 'ServiceStation')
    Service = apps.get_model('main', 'Service')

    for station in ServiceStation.objects.all().iterator():
        ServiceStation.objects.filter(pk=station.pk).update(
            name_norm=main.textnorm.fold_text(station.name),
            city_norm=main.textnorm.fold_text(station.city),
        )

    for service in Service.objects.all().iterator():
        Service.objects.filter(pk=service.pk).update(
            service_name_norm=main.textnorm.fold_text(service.service_name),
        )


def rollback_norm_fields(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0018_review_owner_response_review_photo_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='servicestation',
            name='name_norm',
            field=models.CharField(blank=True, db_index=True, default='', editable=False, max_length=150, verbose_name='Назва (нормалізована)'),
        ),
        migrations.AddField(
            model_name='servicestation',
            name='city_norm',
            field=models.CharField(blank=True, db_index=True, default='', editable=False, max_length=150, verbose_name='Місто (нормалізоване)'),
        ),
        migrations.AddField(
            model_name='service',
            name='service_name_norm',
            field=models.CharField(blank=True, db_index=True, default='', editable=False, max_length=150, verbose_name='Назва послуги (нормалізована)'),
        ),
        migrations.RunPython(backfill_norm_fields, rollback_norm_fields),
    ]
