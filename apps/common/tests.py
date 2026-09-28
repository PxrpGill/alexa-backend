import os
import shutil
import tempfile
from io import BytesIO
from unittest.mock import patch

import requests

from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings
from PIL import Image

from apps.common.images import generate_image_variants
from apps.common.max import (
    MaxDeliveryError,
    admin_change_url,
    format_lead_message,
    queue_max_notification,
    send_max_message,
)
from apps.common.schemas import build_picture_format
from apps.common.tasks import generate_image_variants_task, send_max_notification_task
from apps.common.test_utils import FieldFileStub, make_test_image
from apps.common.throttling import get_client_ip, throttle
from apps.common.typography import typograph_html, typograph_text
from apps.appointments.models import Appointment
from apps.branch.models import BranchModel
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


class GetClientIpTest(TestCase):
    """IP клиента за обратным прокси (apps/common/throttling.get_client_ip)."""

    def _request(self, **meta):
        request = RequestFactory().post('/api/v1/appointments')
        request.META.update(meta)
        return request

    @override_settings(TRUST_PROXY_HEADERS=True)
    def test_prefers_x_real_ip(self):
        request = self._request(
            REMOTE_ADDR='172.18.0.5',
            HTTP_X_REAL_IP='203.0.113.7',
            HTTP_X_FORWARDED_FOR='198.51.100.1, 203.0.113.7',
        )
        self.assertEqual(get_client_ip(request), '203.0.113.7')

    @override_settings(TRUST_PROXY_HEADERS=True)
    def test_takes_last_forwarded_for_hop(self):
        # Первый элемент цепочки подделан клиентом, последний добавил наш nginx.
        request = self._request(
            REMOTE_ADDR='172.18.0.5',
            HTTP_X_FORWARDED_FOR='1.2.3.4, 203.0.113.7',
        )
        self.assertEqual(get_client_ip(request), '203.0.113.7')

    @override_settings(TRUST_PROXY_HEADERS=False)
    def test_ignores_headers_without_proxy(self):
        request = self._request(
            REMOTE_ADDR='192.0.2.10',
            HTTP_X_REAL_IP='203.0.113.7',
        )
        self.assertEqual(get_client_ip(request), '192.0.2.10')

    @override_settings(TRUST_PROXY_HEADERS=True)
    def test_falls_back_to_remote_addr(self):
        self.assertEqual(get_client_ip(self._request(REMOTE_ADDR='192.0.2.11')), '192.0.2.11')


class ThrottleDecoratorTest(TestCase):
    """Лимит считается по IP клиента, а не по адресу контейнера nginx."""

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

        @throttle(2, 60, message='stop')
        def view(request):
            return 200, {'message': 'ok'}

        self.view = view

    def _request(self, ip):
        request = RequestFactory().post('/api/v1/appointments')
        request.META.update(REMOTE_ADDR='172.18.0.5', HTTP_X_REAL_IP=ip)
        return request

    @override_settings(TRUST_PROXY_HEADERS=True)
    @patch('apps.common.throttling.sys.argv', ['manage.py', 'runserver'])
    def test_limits_per_client_ip(self):
        self.assertEqual(self.view(self._request('203.0.113.1'))[0], 200)
        self.assertEqual(self.view(self._request('203.0.113.1'))[0], 200)
        status, body = self.view(self._request('203.0.113.1'))
        self.assertEqual(status, 429)
        self.assertEqual(body['message'], 'stop')

        # Другой клиент за тем же nginx не должен быть заблокирован.
        self.assertEqual(self.view(self._request('203.0.113.2'))[0], 200)


@override_settings(
    MAX_API_URL="https://botapi.max.ru",
    MAX_BOT_TOKEN="token-123",
    MAX_CHAT_ID="-100500",
)
class SendMaxMessageTest(TestCase):
    @patch("apps.common.max.requests.post")
    def test_posts_text_to_max_bot_api(self, post):
        send_max_message("привет")

        post.assert_called_once()
        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://botapi.max.ru/messages")
        self.assertEqual(
            kwargs["params"], {"access_token": "token-123", "chat_id": "-100500"}
        )
        self.assertEqual(kwargs["json"], {"text": "привет"})
        self.assertEqual(kwargs["timeout"], 10)

    @patch("apps.common.max.requests.post")
    def test_raises_on_error_response(self, post):
        post.return_value.ok = False
        post.return_value.status_code = 500

        with self.assertRaises(MaxDeliveryError):
            send_max_message("привет")

    @patch("apps.common.max.requests.post")
    def test_error_never_leaks_bot_token(self, post):
        post.return_value.ok = False
        post.return_value.status_code = 500

        with self.assertRaises(MaxDeliveryError) as ctx:
            send_max_message("привет")

        self.assertNotIn("token-123", str(ctx.exception))

    @patch("apps.common.max.requests.post")
    def test_network_error_never_leaks_bot_token(self, post):
        post.side_effect = requests.ConnectionError(
            "failed for url: https://botapi.max.ru/messages?access_token=token-123"
        )

        with self.assertRaises(MaxDeliveryError) as ctx:
            send_max_message("привет")

        self.assertNotIn("token-123", str(ctx.exception))

    @override_settings(MAX_API_URL="https://botapi.max.ru/")
    @patch("apps.common.max.requests.post")
    def test_strips_trailing_slash_in_api_url(self, post):
        send_max_message("привет")

        self.assertEqual(post.call_args[0][0], "https://botapi.max.ru/messages")


class QueueMaxNotificationTest(TestCase):
    @override_settings(MAX_NOTIFICATIONS_ENABLED=False)
    @patch("apps.common.tasks.send_max_notification_task.delay")
    def test_does_nothing_when_integration_disabled(self, delay):
        queue_max_notification("привет")

        delay.assert_not_called()

    @override_settings(MAX_NOTIFICATIONS_ENABLED=True)
    @patch("apps.common.tasks.send_max_notification_task.delay")
    def test_queues_task_when_enabled(self, delay):
        queue_max_notification("привет")

        delay.assert_called_once_with("привет")

    @override_settings(MAX_NOTIFICATIONS_ENABLED=True)
    @patch("apps.common.tasks.send_max_notification_task.delay")
    def test_swallows_broker_errors(self, delay):
        delay.side_effect = OSError("broker is down")

        queue_max_notification("привет")  # исключение наружу не летит


class SendMaxNotificationTaskTest(TestCase):
    @override_settings(
        MAX_API_URL="https://botapi.max.ru",
        MAX_BOT_TOKEN="token-123",
        MAX_CHAT_ID="-100500",
    )
    @patch("apps.common.max.requests.post")
    def test_task_sends_message(self, post):
        send_max_notification_task("привет")

        post.assert_called_once()


@override_settings(SITE_URL="https://alexa.ru")
class FormatLeadMessageTest(TestCase):
    def setUp(self):
        self.branch = BranchModel.objects.create(name="Центральный")
        self.appointment = Appointment.objects.create(
            patient_name="Иван Иванов",
            patient_phone="+79991234567",
            branch=self.branch,
            is_privacy_agreement=True,
        )

    def test_admin_change_url_points_to_object(self):
        url = admin_change_url(self.appointment)

        self.assertEqual(
            url,
            f"https://alexa.ru/admin/appointments/appointment/{self.appointment.pk}/change/",
        )

    @override_settings(SITE_URL="https://alexa.ru/")
    def test_admin_change_url_strips_trailing_slash(self):
        url = admin_change_url(self.appointment)

        self.assertNotIn("//admin", url.replace("https://", ""))

    def test_message_contains_title_rows_and_admin_link(self):
        text = format_lead_message(
            "🦷 Новая запись на приём",
            [("Имя", "Иван Иванов"), ("Телефон", "+79991234567")],
            self.appointment,
        )

        lines = text.split("\n")
        self.assertEqual(lines[0], "🦷 Новая запись на приём")
        self.assertIn("Имя: Иван Иванов", text)
        self.assertIn("Телефон: +79991234567", text)
        self.assertIn(
            f"Открыть в админке: https://alexa.ru/admin/appointments/appointment/{self.appointment.pk}/change/",
            text,
        )

    def test_message_skips_empty_rows(self):
        text = format_lead_message(
            "🦷 Новая запись на приём",
            [("Имя", "Иван Иванов"), ("Филиал", None), ("Страница", "")],
            self.appointment,
        )

        self.assertNotIn("Филиал", text)
        self.assertNotIn("Страница", text)
        self.assertNotIn("None", text)


@override_settings(MAX_API_URL="https://botapi.max.ru")
class SendMaxMessageWithoutCredentialsTest(TestCase):
    @override_settings(MAX_BOT_TOKEN="", MAX_CHAT_ID="-100500")
    @patch("apps.common.max.requests.post")
    def test_does_not_call_api_without_token(self, post):
        send_max_message("привет")

        post.assert_not_called()

    @override_settings(MAX_BOT_TOKEN="token-123", MAX_CHAT_ID="")
    @patch("apps.common.max.requests.post")
    def test_does_not_call_api_without_chat_id(self, post):
        send_max_message("привет")

        post.assert_not_called()


class CeleryBrokerPublishTest(TestCase):
    """Постановка задачи лежит на пути ответа лид-формы (ATOMIC_REQUESTS выключен,
    поэтому on_commit выполняется сразу), значит зависший брокер не должен
    держать запрос дольше пары секунд."""

    def test_publish_does_not_retry_and_has_socket_timeouts(self):
        from config.celery import app

        self.assertFalse(app.conf.task_publish_retry)
        options = app.conf.broker_transport_options
        self.assertEqual(options.get("socket_connect_timeout"), 2)
        self.assertEqual(options.get("socket_timeout"), 2)
