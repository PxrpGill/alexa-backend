from django.test import Client, TestCase


class APISmokeTest(TestCase):
    """Все роутеры зарегистрированы и отдаются в OpenAPI.

    Пути указаны ровно так, как их отдаёт ninja: APPEND_SLASH = False, поэтому
    у doctors/branches они со слэшем, у остальных — без. При переименовании
    роутов править здесь.
    """

    EXPECTED_PATHS = [
        '/api/v1/doctors/',
        '/api/v1/doctors/{doctor_id}/',
        '/api/v1/branches/',
        '/api/v1/blog',
        '/api/v1/blog/{slug}',
        '/api/v1/promotions',
        '/api/v1/promotions/{slug}',
        '/api/v1/promotions/request',
        '/api/v1/appointments',
        '/api/v1/dms',
        '/api/v1/consultation',
        '/api/v1/vacancies',
        '/api/v1/vacancies/{slug}',
        '/api/v1/vacancies/apply',
        '/api/v1/vacancies/{slug}/apply',
    ]

    # Публичные формы должны быть под rate limit (apps/common/throttling.py).
    THROTTLED_POST_PATHS = [
        '/api/v1/appointments',
        '/api/v1/dms',
        '/api/v1/consultation',
        '/api/v1/promotions/request',
        '/api/v1/vacancies/apply',
        '/api/v1/vacancies/{slug}/apply',
    ]

    def setUp(self):
        self.client = Client()

    def test_docs_endpoint_accessible(self):
        response = self.client.get('/api/v1/docs')
        self.assertIn(response.status_code, [200, 301, 302])

    def test_openapi_schema_accessible(self):
        response = self.client.get('/api/v1/openapi.json')
        self.assertEqual(response.status_code, 200)

        paths = response.json().get('paths', {})
        missing = [path for path in self.EXPECTED_PATHS if path not in paths]
        self.assertEqual(missing, [], f'нет в OpenAPI: {missing}')

    def test_lead_form_endpoints_declare_429(self):
        paths = self.client.get('/api/v1/openapi.json').json()['paths']

        without_429 = [
            path
            for path in self.THROTTLED_POST_PATHS
            if '429' not in paths[path]['post']['responses']
        ]
        self.assertEqual(
            without_429, [], f'нет ответа 429 (throttling): {without_429}'
        )
