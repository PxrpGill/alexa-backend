from django.test import TestCase, Client
from django.utils import timezone
from apps.blog.models import BlogCategory, BlogPost


class BlogModelTest(TestCase):
    def setUp(self):
        self.category = BlogCategory.objects.create(name='Новости', slug='news')
        self.post = BlogPost.objects.create(
            title='Тест',
            slug='test',
            category=self.category,
            excerpt='Краткое описание',
            content='<p>Полный текст</p>',
            status=BlogPost.Status.PUBLISHED,
            published_at=timezone.now(),
        )

    def test_post_str(self):
        self.assertEqual(str(self.post), 'Тест')

    def test_category_str(self):
        self.assertEqual(str(self.category), 'Новости')


class BlogAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        category = BlogCategory.objects.create(name='Новости', slug='news')
        self.published = BlogPost.objects.create(
            title='Опубликовано', slug='published', category=category,
            excerpt='Анонс', content='<p>Текст</p>',
            status=BlogPost.Status.PUBLISHED, published_at=timezone.now(),
        )
        BlogPost.objects.create(
            title='Черновик', slug='draft', category=category,
            excerpt='Анонс', content='<p>Текст</p>',
            status=BlogPost.Status.DRAFT,
        )

    def test_list_returns_only_published(self):
        response = self.client.get('/api/v1/blog/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]['title'], 'Опубликовано')

    def test_get_post_by_slug(self):
        response = self.client.get('/api/v1/blog/published/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['slug'], 'published')

    def test_get_draft_returns_404(self):
        response = self.client.get('/api/v1/blog/draft/')
        self.assertEqual(response.status_code, 404)
