import shutil
import tempfile
from django.test import TestCase, Client, override_settings
from django.utils import timezone
from apps.blog.models import BlogCategory, BlogPost
from apps.common.test_utils import make_test_image


class BlogModelTest(TestCase):
    def setUp(self):
        self.category = BlogCategory.objects.create(name='Новости', slug='news')
        self.post = BlogPost.objects.create(
            title='Тест',
            slug='test',
            category=self.category,
            description='Краткое описание',
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
            description='Анонс', content='<p>Текст</p>',
            status=BlogPost.Status.PUBLISHED, published_at=timezone.now(),
        )
        BlogPost.objects.create(
            title='Черновик', slug='draft', category=category,
            description='Анонс', content='<p>Текст</p>',
            status=BlogPost.Status.DRAFT,
        )

    def test_list_returns_only_published(self):
        response = self.client.get('/api/v1/blog')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['pagination']['total'], 1)
        self.assertEqual(len(data['items']), 1)
        self.assertEqual(data['items'][0]['title'], 'Опубликовано')

    def test_list_response_uses_camel_case_fields(self):
        response = self.client.get('/api/v1/blog')
        item = response.json()['items'][0]
        for key in ('previewPoster', 'poster', 'description', 'publishDate'):
            self.assertIn(key, item)

    def test_get_post_by_slug(self):
        response = self.client.get('/api/v1/blog/published')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['slug'], 'published')
        self.assertIn('content', data)

    def test_get_draft_returns_404(self):
        response = self.client.get('/api/v1/blog/draft')
        self.assertEqual(response.status_code, 404)


class BlogPaginationTest(TestCase):
    def setUp(self):
        self.client = Client()
        category = BlogCategory.objects.create(name='Новости', slug='news')
        for i in range(5):
            BlogPost.objects.create(
                title=f'Пост {i}', slug=f'post-{i}', category=category,
                description='Анонс', content='<p>Текст</p>',
                status=BlogPost.Status.PUBLISHED, published_at=timezone.now(),
            )

    def test_default_pagination(self):
        response = self.client.get('/api/v1/blog')
        data = response.json()
        pagination = data['pagination']
        self.assertEqual(pagination['total'], 5)
        self.assertEqual(pagination['perPage'], 10)
        self.assertEqual(pagination['totalPages'], 1)
        self.assertEqual(len(data['items']), 5)

    def test_per_page_slices_results(self):
        response = self.client.get('/api/v1/blog?perPage=2')
        data = response.json()
        self.assertEqual(len(data['items']), 2)
        self.assertEqual(data['pagination']['totalPages'], 3)
        self.assertEqual(data['pagination']['page'], 1)

    def test_page_param_returns_next_slice(self):
        response = self.client.get('/api/v1/blog?perPage=2&page=2')
        data = response.json()
        self.assertEqual(len(data['items']), 2)
        self.assertEqual(data['pagination']['page'], 2)

    def test_all_pages_ignores_pagination(self):
        response = self.client.get('/api/v1/blog?allPages=true&perPage=2')
        data = response.json()
        self.assertEqual(len(data['items']), 5)
        self.assertEqual(data['pagination']['totalPages'], 1)


class BlogPostPictureFormatAPITest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_root = tempfile.mkdtemp()
        cls.override = override_settings(MEDIA_ROOT=cls.media_root)
        cls.override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.override.disable()
        shutil.rmtree(cls.media_root, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.client = Client()
        category = BlogCategory.objects.create(name='Новости', slug='news-pf')
        self.post = BlogPost.objects.create(
            title='С картинками', slug='with-images', category=category,
            description='Анонс', content='<p>Текст</p>',
            status=BlogPost.Status.PUBLISHED, published_at=timezone.now(),
            preview_poster=make_test_image(name='preview.jpg'),
            preview_poster_mobile=make_test_image(name='preview_m.jpg'),
            poster=make_test_image(name='poster.jpg'),
        )

    def test_preview_poster_matches_picture_format_shape(self):
        response = self.client.get('/api/v1/blog/with-images')
        self.assertEqual(response.status_code, 200)
        preview = response.json()['previewPoster']
        self.assertTrue(preview['original']['src'].endswith('.jpg'))
        self.assertTrue(preview['original']['mobile'].endswith('.jpg'))
        self.assertTrue(preview['webp']['src'].endswith('.webp'))

    def test_poster_without_mobile_has_none_mobile(self):
        response = self.client.get('/api/v1/blog/with-images')
        poster = response.json()['poster']
        self.assertIsNone(poster['original']['mobile'])
        self.assertIsNone(poster['webp']['mobile'])


class BlogPostTypographySaveTest(TestCase):
    def setUp(self):
        self.category = BlogCategory.objects.create(name='Новости', slug='news')

    def test_save_typographs_title_description_and_content(self):
        post = BlogPost.objects.create(
            title='Зачем устанавливают "коронку"',
            slug='koronka',
            category=self.category,
            description='Москва - столица',
            content='<p style="margin-left:0px;">Привет в Москве - скидка 25&nbsp;%</p>',
            status=BlogPost.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        post.refresh_from_db()
        self.assertEqual(post.title, 'Зачем устанавливают «коронку»')
        self.assertEqual(post.description, 'Москва&nbsp;&mdash; столица')
        self.assertNotIn('style', post.content)
        self.assertEqual(post.content, '<p>Привет в&nbsp;Москве&nbsp;&mdash; скидка 25&nbsp;%</p>')

    def test_update_keeps_typography(self):
        post = BlogPost.objects.create(
            title='Обычный заголовок', slug='obichnyy', category=self.category,
            description='Описание', content='<p>Текст</p>',
            status=BlogPost.Status.PUBLISHED,
        )
        post.title = 'Новый "заголовок"'
        post.save(update_fields=['title'])
        post.refresh_from_db()
        self.assertEqual(post.title, 'Новый «заголовок»')
