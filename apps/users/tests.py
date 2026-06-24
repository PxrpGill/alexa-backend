from django.test import TestCase
from apps.users.models import User


class UserModelTest(TestCase):
    def test_create_superadmin(self):
        user = User.objects.create_user(
            username='admin',
            password='testpass123',
            role=User.Role.SUPERADMIN,
        )
        self.assertEqual(user.role, User.Role.SUPERADMIN)
        self.assertIsNone(user.branch)

    def test_create_branch_manager_without_branch(self):
        user = User.objects.create_user(
            username='manager',
            password='testpass123',
            role=User.Role.BRANCH_MANAGER,
        )
        self.assertEqual(user.role, User.Role.BRANCH_MANAGER)
        self.assertIsNone(user.branch)

    def test_str_representation(self):
        user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            first_name='Иван',
            last_name='Иванов',
        )
        self.assertEqual(str(user), 'Иван Иванов')
