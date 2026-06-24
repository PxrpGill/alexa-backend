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
