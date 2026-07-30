from django.test import TestCase, Client
from django.contrib.auth.hashers import make_password
from main.models import User, ServiceStation
from accounting.models import SparePart
from accounting.supplier_api import search_supplier_parts

class SupplierPartsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Створення тестового власника СТО
        self.station_user = User.objects.create(
            full_name='Власник СТО',
            phone='+380671112233',
            email='station_owner@test.com',
            role='station',
            password=make_password('password123')
        )
        
        self.station = ServiceStation.objects.create(
            name='Тестове СТО',
            address='вул. Центральна, 1',
            city='Київ',
            phone='+380671112233',
            user=self.station_user
        )

    def test_supplier_search_by_sku(self):
        result = search_supplier_parts(query='0986479098')
        self.assertEqual(result['status'], 'success')
        self.assertGreater(result['count'], 0)
        first_part = result['parts'][0]
        self.assertIn('0986479098', first_part['sku'].replace(' ', ''))

    def test_supplier_search_by_name(self):
        result = search_supplier_parts(query='колодки')
        self.assertEqual(result['status'], 'success')
        self.assertGreater(result['count'], 0)

    def test_supplier_search_api_endpoint(self):
        response = self.client.get('/accounting/api/suppliers/parts/search/?query=Brembo')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')

    def test_import_supplier_part_to_inventory(self):
        self.client.force_login(self.station_user)

        response = self.client.post('/accounting/inventory/import-supplier-part/', {
            'station_id': self.station.pk,
            'sku': 'P 85 020',
            'part_name': 'Гальмівні колодки передні',
            'brand': 'Brembo',
            'cost_price': '1250.00',
            'selling_price': '1750.00',
            'quantity': '2'
        })
        self.assertEqual(response.status_code, 302)
        
        part = SparePart.objects.filter(station=self.station, sku='P 85 020').first()
        self.assertIsNotNone(part)
        self.assertEqual(part.quantity, 2)
        self.assertEqual(float(part.cost_price), 1250.00)
