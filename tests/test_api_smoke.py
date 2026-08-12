from django.test import TestCase, Client


class APISmokeTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_docs_endpoint_accessible(self):
        response = self.client.get('/api/v1/docs')
        self.assertIn(response.status_code, [200, 301, 302])

    def test_openapi_schema_accessible(self):
        response = self.client.get('/api/v1/openapi.json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        paths = data.get('paths', {})
        self.assertIn('/api/v1/doctors/', paths)
        self.assertIn('/api/v1/blog/', paths)
        self.assertIn('/api/v1/promotions/', paths)
        self.assertIn('/api/v1/appointments/', paths)
