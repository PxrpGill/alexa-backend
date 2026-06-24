from django.test import TestCase, Client
from apps.branches.models import Branch


class BranchModelTest(TestCase):
    def test_create_branch(self):
        branch = Branch.objects.create(
            name='Центральный',
            address='ул. Ленина, 1',
            phone='+7-999-000-0001',
            email='main@alexa.ru',
        )
        self.assertEqual(str(branch), 'Центральный')
        self.assertTrue(branch.is_active)

    def test_working_hours_defaults_to_empty_dict(self):
        branch = Branch.objects.create(
            name='Северный',
            address='ул. Северная, 5',
            phone='+7-999-000-0002',
            email='north@alexa.ru',
        )
        self.assertEqual(branch.working_hours, {})
        self.assertEqual(branch.coordinates, {})


class BranchAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.branch = Branch.objects.create(
            name='Центральный',
            address='ул. Ленина, 1',
            phone='+7-999-000-0001',
            email='main@alexa.ru',
            is_active=True,
        )
        Branch.objects.create(
            name='Закрытый',
            address='ул. Старая, 9',
            phone='+7-999-000-0009',
            email='old@alexa.ru',
            is_active=False,
        )

    def test_list_branches_returns_only_active(self):
        response = self.client.get('/api/v1/branches/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'Центральный')

    def test_get_branch_detail(self):
        response = self.client.get(f'/api/v1/branches/{self.branch.id}/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['name'], 'Центральный')

    def test_get_inactive_branch_returns_404(self):
        inactive = Branch.objects.get(name='Закрытый')
        response = self.client.get(f'/api/v1/branches/{inactive.id}/')
        self.assertEqual(response.status_code, 404)
