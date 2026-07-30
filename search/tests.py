from django.test import TestCase
from django.urls import reverse


class SearchTestCase(TestCase):
    def test_search_page_loads(self):
        """Перевірка завантаження сторінки пошуку СТО."""
        response = self.client.get(reverse('search:search_stations'))
        self.assertEqual(response.status_code, 200)

    def test_search_with_radius_filter(self):
        """Перевірка фільтрації СТО за відстанню від геопозиції користувача."""
        response = self.client.get(reverse('search:search_stations'), {
            'lat': '50.4501',
            'lng': '30.5234',
            'radius': '10'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('selected_radius', response.context)
        self.assertEqual(response.context['selected_radius'], '10')


