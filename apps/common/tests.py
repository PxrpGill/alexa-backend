import os
import shutil
import tempfile
from io import BytesIO
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.test import TestCase, override_settings
from PIL import Image

from apps.common.images import generate_image_variants
from apps.common.schemas import build_picture_format
from apps.common.tasks import generate_image_variants_task
from apps.common.test_utils import FieldFileStub, make_test_image
from apps.common.typography import typograph_html, typograph_text
from apps.doctors.models import Doctor


class GenerateImageVariantsTest(TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.storage = FileSystemStorage(location=self.tmp_dir, base_url='/media/')

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _save_source(self, name='doctors/photo.jpg', img_format='JPEG', mode='RGB', color='red'):
        buffer = BytesIO()
        Image.new(mode, (10, 10), color=color).save(buffer, format=img_format)
        buffer.seek(0)
        return self.storage.save(name, ContentFile(buffer.read()))

    def test_generates_webp_and_avif_siblings(self):
        saved_name = self._save_source()
        field_file = FieldFileStub(self.storage, saved_name)

        generate_image_variants(field_file)

        self.assertTrue(self.storage.exists('doctors/photo.webp'))
        self.assertTrue(self.storage.exists('doctors/photo.avif'))

    def test_preserves_transparency_for_png(self):
        saved_name = self._save_source(
            name='icons/icon.png', img_format='PNG', mode='RGBA', color=(255, 0, 0, 128),
        )
        field_file = FieldFileStub(self.storage, saved_name)

        generate_image_variants(field_file)

        with self.storage.open('icons/icon.webp', 'rb') as f:
            webp_image = Image.open(f)
            webp_image.load()
            self.assertEqual(webp_image.mode, 'RGBA')

    def test_skips_regeneration_when_variants_already_exist(self):
        saved_name = self._save_source()
        field_file = FieldFileStub(self.storage, saved_name)
        generate_image_variants(field_file)
        webp_path = self.storage.path('doctors/photo.webp')
        first_mtime = os.path.getmtime(webp_path)

        generate_image_variants(field_file)

        self.assertEqual(os.path.getmtime(webp_path), first_mtime)


class BuildPictureFormatTest(TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.storage = FileSystemStorage(location=self.tmp_dir, base_url='/media/')

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _save(self, name, upload):
        return self.storage.save(name, ContentFile(upload.read()))

    def test_returns_none_when_no_source_file(self):
        result = build_picture_format(None)
        self.assertIsNone(result)

    def test_includes_original_webp_avif_after_generation(self):
        name = self._save('doctors/photo.jpg', make_test_image())
        field_file = FieldFileStub(self.storage, name)
        generate_image_variants(field_file)

        result = build_picture_format(field_file)

        self.assertEqual(result.original.src, '/media/doctors/photo.jpg')
        self.assertEqual(result.webp.src, '/media/doctors/photo.webp')
        self.assertEqual(result.avif.src, '/media/doctors/photo.avif')
        self.assertIsNone(result.original.mobile)

    def test_mobile_populated_when_mobile_field_given(self):
        name = self._save('doctors/photo.jpg', make_test_image())
        mobile_name = self._save('doctors/photo_m.jpg', make_test_image(name='m.jpg'))
        field_file = FieldFileStub(self.storage, name)
        mobile_field = FieldFileStub(self.storage, mobile_name)
        generate_image_variants(field_file)
        generate_image_variants(mobile_field)

        result = build_picture_format(field_file, mobile_field)

        self.assertEqual(result.original.mobile, '/media/doctors/photo_m.jpg')
        self.assertEqual(result.webp.mobile, '/media/doctors/photo_m.webp')

    def test_webp_and_avif_omitted_when_variants_missing(self):
        name = self._save('doctors/photo.jpg', make_test_image())
        field_file = FieldFileStub(self.storage, name)

        result = build_picture_format(field_file)

        self.assertIsNone(result.webp)
        self.assertIsNone(result.avif)


class GenerateImageVariantsTaskTest(TestCase):
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

    def test_task_loads_instance_and_generates_variants_for_field(self):
        doctor = Doctor.objects.create(
            first_name='Иван', last_name='Иванов', patronymic='Иванович',
            photo=make_test_image(name='photo.jpg'),
        )

        with patch('apps.common.tasks.generate_image_variants') as mocked:
            generate_image_variants_task('doctors', 'Doctor', doctor.pk, 'photo')

        mocked.assert_called_once()
        called_field_file = mocked.call_args[0][0]
        self.assertEqual(called_field_file.name, doctor.photo.name)

    def test_task_is_noop_for_missing_instance(self):
        with patch('apps.common.tasks.generate_image_variants') as mocked:
            generate_image_variants_task('doctors', 'Doctor', 999999, 'photo')

        mocked.assert_not_called()

    def test_task_is_noop_for_empty_field(self):
        doctor = Doctor.objects.create(
            first_name='Пётр', last_name='Петров', patronymic='Петрович',
        )

        with patch('apps.common.tasks.generate_image_variants') as mocked:
            generate_image_variants_task('doctors', 'Doctor', doctor.pk, 'photo')

        mocked.assert_not_called()


class ImageVariantsMixinEnqueueTest(TestCase):
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

    def test_save_enqueues_task_for_each_nonempty_field(self):
        with patch('apps.common.mixins.generate_image_variants_task') as mocked_task:
            doctor = Doctor.objects.create(
                first_name='Иван', last_name='Иванов', patronymic='Иванович',
                photo=make_test_image(name='photo.jpg'),
            )

        mocked_task.delay.assert_called_once_with('doctors', 'Doctor', doctor.pk, 'photo')

    def test_save_succeeds_even_if_enqueue_raises(self):
        with patch('apps.common.mixins.generate_image_variants_task') as mocked_task:
            mocked_task.delay.side_effect = Exception('брокер недоступен')
            doctor = Doctor.objects.create(
                first_name='Пётр', last_name='Петров', patronymic='Петрович',
                photo=make_test_image(name='photo2.jpg'),
            )

        self.assertIsNotNone(doctor.pk)
        self.assertTrue(Doctor.objects.filter(pk=doctor.pk).exists())


class TypographyTextTest(TestCase):
    def test_converts_double_quotes_to_guillemets(self):
        self.assertEqual(
            typograph_text('Он сказал: "привет" и ушёл'),
            'Он сказал: «привет» и%sушёл' % '\u00A0',
        )

    def test_nested_quotes_become_lapki(self):
        self.assertEqual(
            typograph_text('«внешние «внутренние» кавычки»'),
            '«внешние „внутренние" кавычки»',
        )

    def test_straight_quotes_nested_become_lapki(self):
        self.assertEqual(
            typograph_text('«внешние "внутренние" кавычки»'),
            '«внешние „внутренние" кавычки»',
        )

    def test_existing_top_level_guillemets_preserved(self):
        self.assertEqual(typograph_text('«уже готовая ёлочка»'), '«уже готовая ёлочка»')

    def test_converts_spaced_hyphen_to_em_dash(self):
        self.assertEqual(typograph_text('Москва - столица'), 'Москва%s— столица' % '\u00A0')

    def test_converts_double_hyphen_to_em_dash(self):
        self.assertEqual(typograph_text('Это--пример'), 'Это—пример')

    def test_converts_ellipsis(self):
        self.assertEqual(typograph_text('Ну и дела...'), 'Ну и%sдела…' % '\u00A0')

    def test_adds_nbsp_after_short_preposition(self):
        result = typograph_text('Привет в Москве')
        self.assertIn('в%sМоскве' % '\u00A0', result)

    def test_adds_nbsp_before_percent(self):
        self.assertEqual(typograph_text('Скидка 25 %'), 'Скидка 25%s%%' % '\u00A0')

    def test_glues_number_to_numero_sign(self):
        self.assertEqual(typograph_text('кабинет № 5'), 'кабинет №%s5' % '\u00A0')

    def test_removes_space_before_comma_and_dot(self):
        self.assertEqual(typograph_text('Привет ,мир.'), 'Привет,мир.')

    def test_leaves_regular_hyphen_in_words(self):
        self.assertEqual(typograph_text('кофе-машина'), 'кофе-машина')


class TypographyHtmlTest(TestCase):
    def test_strips_style_attribute(self):
        html = '<h2>Заголовок</h2><p style="margin-left:0px;">Текст</p>'
        result = typograph_html(html)
        self.assertNotIn('style', result)
        self.assertIn('<h2>Заголовок</h2>', result)
        self.assertIn('<p>Текст</p>', result)

    def test_strips_single_quoted_style_attribute(self):
        result = typograph_html('<p style=\'color:red\'>Текст</p>')
        self.assertEqual(result, '<p>Текст</p>')

    def test_typographs_only_text_nodes(self):
        result = typograph_html('<p>Москва - столица</p>')
        self.assertEqual(result, '<p>Москва&nbsp;&mdash; столица</p>')

    def test_preserves_attributes_and_nbsp(self):
        html = '<a href="/x">Скидка 25&nbsp;%</a>'
        result = typograph_html(html)
        self.assertIn('href="/x"', result)
        self.assertIn('25&nbsp;%', result)

    def test_emits_nbsp_and_mdash_entities_in_html(self):
        result = typograph_html('<p>Привет в Москве - скидка</p>')
        self.assertEqual(result, '<p>Привет в&nbsp;Москве&nbsp;&mdash; скидка</p>')

    def test_glues_existing_mdash_entity_with_nbsp(self):
        result = typograph_html('<p>Слово &mdash; это тест</p>')
        self.assertEqual(result, '<p>Слово&nbsp;&mdash; это тест</p>')

    def test_drops_style_block(self):
        html = '<p>Текст</p><style>p { color: red }</style><p>Ещё</p>'
        result = typograph_html(html)
        self.assertNotIn('<style>', result)
        self.assertNotIn('color', result)
        self.assertEqual(result, '<p>Текст</p><p>Ещё</p>')

    def test_returns_original_on_empty(self):
        self.assertEqual(typograph_html(''), '')
        self.assertIsNone(typograph_html(None))
