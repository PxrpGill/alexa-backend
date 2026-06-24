from django.test import TestCase, Client
from datetime import date, timedelta
from apps.branches.models import Branch
from apps.promotions.models import Promotion


class PromotionModelTest(TestCase):
    def setUp(self):
        self.branch = Branch.objects.create(
            name='Центральный', address='ул. Ленина, 1',
            phone='+7-999-000-0001', email='main@alexa.ru',
        )

    def test_promotion_str(self):
        promo = Promotion.objects.create(
            title='Скидка 20%', starts_at=date.today(),
        )
        self.assertEqual(str(promo), 'Скидка 20%')

    def test_promotion_with_branch(self):
        promo = Promotion.objects.create(
            title='Акция для филиала', starts_at=date.today(),
        )
        promo.branches.add(self.branch)
        self.assertIn(self.branch, promo.branches.all())


class PromotionAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.branch = Branch.objects.create(
            name='Центральный', address='ул. Ленина, 1',
            phone='+7-999-000-0001', email='main@alexa.ru',
        )
        today = date.today()
        self.active = Promotion.objects.create(
            title='Активная акция',
            starts_at=today - timedelta(days=1),
            ends_at=today + timedelta(days=5),
            is_active=True,
        )
        self.active.branches.add(self.branch)

        self.expired = Promotion.objects.create(
            title='Устаревшая акция',
            starts_at=today - timedelta(days=10),
            ends_at=today - timedelta(days=1),
            is_active=True,
        )

    def test_list_promotions_returns_only_active(self):
        response = self.client.get('/api/v1/promotions/')
        self.assertEqual(response.status_code, 200)
        titles = [p['title'] for p in response.json()]
        self.assertIn('Активная акция', titles)
        self.assertNotIn('Устаревшая акция', titles)

    def test_filter_by_branch(self):
        response = self.client.get(f'/api/v1/promotions/?branch_id={self.branch.id}')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['title'], 'Активная акция')
