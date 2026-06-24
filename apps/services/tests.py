from django.test import TestCase, Client
from decimal import Decimal
from apps.branches.models import Branch
from apps.services.models import ServiceCategory, Service, BranchService


class ServiceModelTest(TestCase):
    def setUp(self):
        self.branch = Branch.objects.create(
            name='Центральный', address='ул. Ленина, 1',
            phone='+7-999-000-0001', email='main@alexa.ru',
        )
        self.category = ServiceCategory.objects.create(name='Терапия', slug='therapy')
        self.service = Service.objects.create(
            name='Лечение кариеса', slug='caries', category=self.category,
        )

    def test_service_str(self):
        self.assertEqual(str(self.service), 'Лечение кариеса')

    def test_category_str(self):
        self.assertEqual(str(self.category), 'Терапия')

    def test_branch_service_price(self):
        bs = BranchService.objects.create(
            branch=self.branch, service=self.service,
            price=Decimal('3500.00'), price_from=False,
        )
        self.assertEqual(bs.price, Decimal('3500.00'))
        self.assertFalse(bs.price_from)


class ServiceAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.branch = Branch.objects.create(
            name='Центральный', address='ул. Ленина, 1',
            phone='+7-999-000-0001', email='main@alexa.ru',
        )
        self.category = ServiceCategory.objects.create(name='Терапия', slug='therapy')
        self.service = Service.objects.create(
            name='Лечение кариеса', slug='caries', category=self.category, is_active=True,
        )
        BranchService.objects.create(
            branch=self.branch, service=self.service,
            price=Decimal('3500.00'), is_active=True,
        )

    def test_list_categories(self):
        response = self.client.get('/api/v1/services/categories/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_list_services_filtered_by_branch(self):
        response = self.client.get(f'/api/v1/services/?branch_id={self.branch.id}')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['price'], '3500.00')

    def test_list_services_filtered_by_category(self):
        response = self.client.get('/api/v1/services/?category=therapy')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_inactive_branchservice_excluded(self):
        branch2 = Branch.objects.create(
            name='Северный', address='ул. Северная, 5',
            phone='+7-999-000-0002', email='north@alexa.ru',
        )
        BranchService.objects.create(
            branch=branch2, service=self.service,
            price=Decimal('4000.00'), is_active=False,
        )
        response = self.client.get(f'/api/v1/services/?branch_id={branch2.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)
