from django.test import TestCase, Client
from main.vin_decoder import decode_vin

class VINDecoderTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_valid_vin_pattern_decoder(self):
        # VIN для Ford Mustang 2017 року
        vin = '1FA6P8CF0H5123456'
        result = decode_vin(vin)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['brand'], 'Ford')
        self.assertEqual(result['year'], 2017)

    def test_bmw_vin_decoder(self):
        # VIN для BMW 2021 року
        vin = 'WBA123456M0000000'
        result = decode_vin(vin)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['brand'], 'BMW')
        self.assertEqual(result['year'], 2021)

    def test_invalid_vin_length(self):
        vin = 'TOO_SHORT_VIN'
        result = decode_vin(vin)
        self.assertEqual(result['status'], 'error')
        self.assertIn('17 символів', result['message'])

    def test_vin_decoder_api_endpoint(self):
        response = self.client.get('/api/vin/decode/?vin=WVWZZZ3CZAE123456')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['brand'], 'Volkswagen')
