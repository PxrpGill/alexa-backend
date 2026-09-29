from django.test import Client, TestCase

from apps.branch.models import BranchModel


class BranchTypographyTest(TestCase):
    """Название филиала типографируется при отдаче, slug — нет."""

    def setUp(self):
        self.client = Client()
        BranchModel.objects.create(name='Алекса "Центр" - на Ленина')

    def test_api_typographs_name_and_keeps_slug(self):
        data = self.client.get('/api/v1/branches/').json()
        self.assertEqual(data[0]['name'], 'Алекса «Центр»&nbsp;&mdash; на&nbsp;Ленина')
        self.assertNotIn('&mdash;', data[0]['slug'])

    def test_db_keeps_original_name(self):
        branch = BranchModel.objects.get()
        self.assertEqual(branch.name, 'Алекса "Центр" - на Ленина')
