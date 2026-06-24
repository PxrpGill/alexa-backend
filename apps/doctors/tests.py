from django.test import TestCase, Client
from apps.branches.models import Branch
from apps.doctors.models import Doctor, Specialization, DoctorBranch


class DoctorModelTest(TestCase):
    def setUp(self):
        self.spec = Specialization.objects.create(name='Терапевт')
        self.doctor = Doctor.objects.create(
            first_name='Иван',
            last_name='Иванов',
            patronymic='Иванович',
        )
        self.branch = Branch.objects.create(
            name='Центральный',
            address='ул. Ленина, 1',
            phone='+7-999-000-0001',
            email='main@alexa.ru',
        )

    def test_str_representation(self):
        self.assertEqual(str(self.doctor), 'Иванов Иван Иванович')

    def test_specialization_str(self):
        self.assertEqual(str(self.spec), 'Терапевт')

    def test_doctor_branch_relationship(self):
        db = DoctorBranch.objects.create(doctor=self.doctor, branch=self.branch)
        self.assertEqual(db.doctor, self.doctor)
        self.assertEqual(db.branch, self.branch)
        self.assertTrue(db.is_active)
        self.assertEqual(db.schedule, {})


class DoctorAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.branch = Branch.objects.create(
            name='Центральный',
            address='ул. Ленина, 1',
            phone='+7-999-000-0001',
            email='main@alexa.ru',
            is_active=True,
        )
        self.doctor1 = Doctor.objects.create(
            first_name='Иван', last_name='Иванов', patronymic='Иванович', is_active=True
        )
        self.doctor2 = Doctor.objects.create(
            first_name='Мария', last_name='Петрова', patronymic='Сергеевна', is_active=True
        )
        Doctor.objects.create(
            first_name='Игорь', last_name='Сидоров', patronymic='Петрович', is_active=False
        )

    def test_list_all_doctors(self):
        response = self.client.get('/api/v1/doctors/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)

    def test_filter_doctors_by_branch(self):
        DoctorBranch.objects.create(doctor=self.doctor1, branch=self.branch, is_active=True)
        response = self.client.get(f'/api/v1/doctors/?branch_id={self.branch.id}')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['last_name'], 'Иванов')

    def test_get_doctor_detail(self):
        response = self.client.get(f'/api/v1/doctors/{self.doctor1.id}/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['last_name'], 'Иванов')

    def test_inactive_doctor_returns_404(self):
        inactive = Doctor.objects.create(
            first_name='Игорь', last_name='Сидоров', patronymic='Петрович', is_active=False
        )
        response = self.client.get(f'/api/v1/doctors/{inactive.id}/')
        self.assertEqual(response.status_code, 404)

    def test_filter_excludes_inactive_doctorbranch(self):
        DoctorBranch.objects.create(doctor=self.doctor2, branch=self.branch, is_active=False)
        response = self.client.get(f'/api/v1/doctors/?branch_id={self.branch.id}')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 0)
