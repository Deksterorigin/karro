from django.core.management.base import BaseCommand

from main.models import Service, ServiceStation


class Command(BaseCommand):
    help = 'Перераховує нормалізовані поля пошуку (name_norm, city_norm, service_name_norm)'

    def handle(self, *args, **options):
        stations_count = 0
        for station in ServiceStation.objects.all().iterator():
            station.save(update_fields=['name_norm', 'city_norm'])
            stations_count += 1

        services_count = 0
        for service in Service.objects.all().iterator():
            service.save(update_fields=['service_name_norm'])
            services_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Оновлено СТО: {stations_count}, послуг: {services_count}'
        ))
