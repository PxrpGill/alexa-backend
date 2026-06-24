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
