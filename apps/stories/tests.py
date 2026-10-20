import os
import shutil
import subprocess
import tempfile
from datetime import timedelta
from unittest import skipUnless
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from apps.common.test_utils import make_test_image
from apps.stories.media import MediaProcessingError
from apps.stories.models import StoryGroup, StoryItem
from apps.users.models import User

HAS_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
READY = StoryItem.ProcessingStatus.READY


def make_test_video(seconds=1, size="180x320"):
    """Короткий вертикальный mp4 с тоном — сгенерирован самим ffmpeg."""
    tmp_dir = tempfile.mkdtemp()
    path = os.path.join(tmp_dir, "clip.mp4")
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error",
            "-f", "lavfi", "-i", f"testsrc=size={size}:rate=25:duration={seconds}",
            "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
            path,
        ],
        check=True,
    )
    with open(path, "rb") as fh:
        content = fh.read()
    shutil.rmtree(tmp_dir)
    return SimpleUploadedFile("clip.mp4", content, content_type="video/mp4")


class StoriesTestCase(TestCase):
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

    def make_group(self, **kwargs):
        kwargs.setdefault("title", "О клинике")
        kwargs.setdefault("is_published", True)
        with self.captureOnCommitCallbacks(execute=True):
            return StoryGroup.objects.create(
                preview=make_test_image("preview.jpg", size=(1000, 1000)), **kwargs
            )

    def make_image_item(self, group, **kwargs):
        with self.captureOnCommitCallbacks(execute=True):
            return StoryItem.objects.create(
                group=group,
                type=StoryItem.Type.IMAGE,
                image=make_test_image("frame.jpg", size=(1080, 1920)),
                **kwargs,
            )

    def get_groups(self):
        response = self.client.get("/api/v1/stories")
        self.assertEqual(response.status_code, 200)
        return response.json()["groups"]


class StoryImageProcessingTest(StoriesTestCase):
    def test_image_item_becomes_ready_with_variants_and_mobile_copy(self):
        item = self.make_image_item(self.make_group())
        item.refresh_from_db()

        self.assertEqual(item.processing_status, READY)
        storage = item.image.storage
        base, ext = os.path.splitext(item.image.name)
        for name in (
            f"{base}.webp", f"{base}.avif",
            f"{base}-m{ext}", f"{base}-m.webp", f"{base}-m.avif",
        ):
            self.assertTrue(storage.exists(name), name)

    def test_same_base_name_with_different_extensions_does_not_share_variants(self):
        # photo.png и photo.jpg раньше делили photo.webp/photo.avif: вторая загрузка
        # видела готовые варианты и отдавала картинку первой.
        group = self.make_group()
        with self.captureOnCommitCallbacks(execute=True):
            png = StoryItem.objects.create(
                group=group,
                image=make_test_image("photo.png", img_format="PNG", size=(20, 20)),
            )
        with self.captureOnCommitCallbacks(execute=True):
            jpg = StoryItem.objects.create(
                group=group, image=make_test_image("photo.jpg", size=(30, 30))
            )

        posters = [i["poster"] for i in self.get_groups()[0]["items"]]
        self.assertEqual(len(posters), 2)
        for key in ("webp", "avif"):
            self.assertNotEqual(posters[0][key]["src"], posters[1][key]["src"])
            self.assertNotEqual(posters[0][key]["mobile"], posters[1][key]["mobile"])
        self.assertNotEqual(
            os.path.splitext(png.image.name)[0], os.path.splitext(jpg.image.name)[0]
        )

    def test_mobile_copy_is_downscaled_to_750(self):
        from PIL import Image

        item = self.make_image_item(self.make_group())
        base, ext = os.path.splitext(item.image.name)
        with item.image.storage.open(f"{base}-m{ext}") as fh:
            self.assertEqual(Image.open(fh).size, (750, 1333))

    def test_replacing_media_resets_status(self):
        item = self.make_image_item(self.make_group())
        with patch("apps.stories.tasks.process_story_item_task.delay") as delay:
            with self.captureOnCommitCallbacks(execute=True):
                item.image = make_test_image("other.jpg", size=(1080, 1920))
                item.save()
        item.refresh_from_db()
        self.assertEqual(item.processing_status, StoryItem.ProcessingStatus.PENDING)
        delay.assert_called_once_with(item.pk)

    def test_saving_without_media_change_keeps_status(self):
        item = self.make_image_item(self.make_group())
        with patch("apps.stories.tasks.process_story_item_task.delay") as delay:
            with self.captureOnCommitCallbacks(execute=True):
                item.duration = 5000
                item.save()
        item.refresh_from_db()
        self.assertEqual(item.processing_status, READY)
        delay.assert_not_called()

    def test_broker_failure_does_not_break_save(self):
        group = self.make_group()
        with patch(
            "apps.stories.tasks.process_story_item_task.delay",
            side_effect=ConnectionError("broker down"),
        ):
            with self.captureOnCommitCallbacks(execute=True):
                item = StoryItem.objects.create(
                    group=group, image=make_test_image("frame.jpg")
                )
        self.assertEqual(item.processing_status, StoryItem.ProcessingStatus.PENDING)


class StoryVideoProcessingTest(StoriesTestCase):
    def test_transcode_failure_marks_error(self):
        group = self.make_group()
        with patch(
            "apps.stories.tasks.transcode_story_video",
            side_effect=MediaProcessingError("ffmpeg завершился с кодом 1"),
        ):
            with self.captureOnCommitCallbacks(execute=True):
                item = StoryItem.objects.create(
                    group=group,
                    type=StoryItem.Type.VIDEO,
                    video=SimpleUploadedFile("clip.mp4", b"not a video"),
                )
        item.refresh_from_db()
        self.assertEqual(item.processing_status, StoryItem.ProcessingStatus.ERROR)
        self.assertIn("ffmpeg", item.processing_error)
        self.assertEqual(self.get_groups(), [])

    @skipUnless(HAS_FFMPEG, "нужен ffmpeg")
    def test_video_is_transcoded_and_served(self):
        group = self.make_group()
        with self.captureOnCommitCallbacks(execute=True):
            item = StoryItem.objects.create(
                group=group, type=StoryItem.Type.VIDEO, video=make_test_video()
            )
        item.refresh_from_db()
        self.assertEqual(item.processing_status, READY, item.processing_error)

        for field in (item.video_src, item.video_mobile, item.video_poster):
            self.assertTrue(field.storage.exists(field.name), field.name)
        self.assertTrue(item.video_src.name.endswith("-src.mp4"))
        self.assertTrue(item.video_mobile.name.endswith("-m.mp4"))
        self.assertTrue(item.video_poster.name.endswith("-poster.webp"))

        probe = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries",
                "stream=codec_name", "-of", "csv=p=0", item.video_src.path,
            ],
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(probe.stdout.split(), ["h264", "aac"])

        [video] = self.get_groups()[0]["items"]
        self.assertEqual(
            video,
            {
                "id": item.pk,
                "type": "video",
                "source": {"src": item.video_src.url, "mobile": item.video_mobile.url},
                "posterSrc": item.video_poster.url,
            },
        )

    @skipUnless(HAS_FFMPEG, "нужен ffmpeg")
    def test_clean_rejects_video_longer_than_limit(self):
        item = StoryItem(
            group=self.make_group(),
            type=StoryItem.Type.VIDEO,
            video=make_test_video(seconds=3),
        )
        with override_settings(MAX_STORY_VIDEO_SECONDS=2):
            with self.assertRaises(ValidationError) as ctx:
                item.full_clean()
        self.assertIn("2 секунд", str(ctx.exception.message_dict["video"]))

    @skipUnless(HAS_FFMPEG, "нужен ffmpeg")
    def test_clean_rejects_unreadable_video(self):
        item = StoryItem(
            group=self.make_group(),
            type=StoryItem.Type.VIDEO,
            video=SimpleUploadedFile("clip.mp4", b"not a video"),
        )
        with self.assertRaises(ValidationError) as ctx:
            item.full_clean()
        self.assertIn("Не удалось прочитать", str(ctx.exception.message_dict["video"]))

    @override_settings(MAX_STORY_VIDEO_SIZE=10)
    def test_clean_rejects_too_big_video(self):
        item = StoryItem(
            group=self.make_group(),
            type=StoryItem.Type.VIDEO,
            video=SimpleUploadedFile("clip.mp4", b"x" * 11),
        )
        with self.assertRaises(ValidationError) as ctx:
            item.full_clean()
        self.assertIn("МБ", str(ctx.exception.message_dict["video"]))


class StoryItemValidationTest(StoriesTestCase):
    def assert_clean_errors(self, item, fields):
        with self.assertRaises(ValidationError) as ctx:
            item.full_clean()
        self.assertEqual(set(ctx.exception.message_dict), set(fields))

    def test_image_requires_image_and_no_video(self):
        group = self.make_group()
        self.assert_clean_errors(StoryItem(group=group, type="image"), {"image"})
        self.assert_clean_errors(
            StoryItem(
                group=group,
                type="image",
                image=make_test_image(),
                video=SimpleUploadedFile("clip.mp4", b"x"),
            ),
            {"video"},
        )

    def test_video_requires_video_and_no_image_or_duration(self):
        group = self.make_group()
        self.assert_clean_errors(StoryItem(group=group, type="video"), {"video"})
        with patch("apps.stories.models.probe_uploaded_duration", return_value=5.0):
            self.assert_clean_errors(
                StoryItem(
                    group=group,
                    type="video",
                    video=SimpleUploadedFile("clip.mp4", b"x"),
                    image=make_test_image(),
                    duration=5000,
                ),
                {"image", "duration"},
            )

    def test_video_extension_is_validated(self):
        with patch("apps.stories.models.probe_uploaded_duration", return_value=5.0):
            self.assert_clean_errors(
                StoryItem(
                    group=self.make_group(),
                    type="video",
                    video=SimpleUploadedFile("clip.avi", b"x"),
                ),
                {"video"},
            )

    def test_duration_range(self):
        group = self.make_group()
        for duration in (1999, 30001):
            self.assert_clean_errors(
                StoryItem(group=group, image=make_test_image(), duration=duration),
                {"duration"},
            )
        StoryItem(group=group, image=make_test_image(), duration=2000).full_clean()

    def test_title_max_length(self):
        group = StoryGroup(title="я" * 31, preview=make_test_image())
        with self.assertRaises(ValidationError) as ctx:
            group.full_clean()
        self.assertIn("title", ctx.exception.message_dict)

    def test_publish_window_order(self):
        now = timezone.now()
        group = StoryGroup(
            preview=make_test_image(),
            publish_from=now,
            publish_to=now - timedelta(days=1),
        )
        with self.assertRaises(ValidationError) as ctx:
            group.full_clean()
        self.assertIn("publish_to", ctx.exception.message_dict)


class StoriesAPITest(StoriesTestCase):
    def test_contract(self):
        group = self.make_group()
        item = self.make_image_item(group, duration=4000)
        group.refresh_from_db()

        [data] = self.get_groups()
        self.assertEqual(set(data), {"id", "title", "updatedAt", "preview", "items"})
        self.assertEqual(data["id"], group.pk)
        self.assertEqual(data["title"], "О&nbsp;клинике")
        self.assertTrue(data["updatedAt"].endswith("Z"))
        self.assertEqual(
            set(data["preview"]["webp"]), {"src", "mobile"}
        )
        self.assertTrue(data["preview"]["webp"]["src"].startswith("/media/stories/"))
        self.assertTrue(data["preview"]["webp"]["mobile"].endswith("-m.webp"))

        [frame] = data["items"]
        self.assertEqual(frame["id"], item.pk)
        self.assertEqual(frame["type"], "image")
        self.assertEqual(frame["duration"], 4000)
        self.assertEqual(set(frame["poster"]), {"original", "webp", "avif"})
        self.assertTrue(frame["poster"]["avif"]["mobile"].endswith("-m.avif"))

    def test_null_fields_are_omitted(self):
        group = self.make_group(title="")
        self.make_image_item(group)

        [data] = self.get_groups()
        self.assertNotIn("title", data)
        self.assertNotIn("duration", data["items"][0])

    def test_filters_unpublished_and_window(self):
        now = timezone.now()
        hour = timedelta(hours=1)
        visible = [
            self.make_group(title="Всегда"),
            self.make_group(title="Сейчас", publish_from=now - hour, publish_to=now + hour),
            self.make_group(title="Без конца", publish_from=now - hour),
        ]
        hidden = [
            self.make_group(title="Черновик", is_published=False),
            self.make_group(title="Будущая", publish_from=now + hour),
            self.make_group(title="Прошла", publish_to=now - hour),
        ]
        for group in visible + hidden:
            self.make_image_item(group)

        ids = [g["id"] for g in self.get_groups()]
        self.assertEqual(ids, [g.pk for g in visible])

    def test_groups_without_ready_items_are_hidden(self):
        self.make_group(title="Пустая")
        with_pending = self.make_group(title="В обработке")
        with patch("apps.stories.tasks.process_story_item_task.delay"):
            with self.captureOnCommitCallbacks(execute=True):
                pending = StoryItem.objects.create(
                    group=with_pending, image=make_test_image("frame.jpg")
                )
        self.assertEqual(self.get_groups(), [])

        ready = self.make_image_item(with_pending)
        [data] = self.get_groups()
        self.assertEqual([i["id"] for i in data["items"]], [ready.pk])
        self.assertNotEqual(ready.pk, pending.pk)

    def test_ordering(self):
        second = self.make_group(title="Вторая", order=2)
        first = self.make_group(title="Первая", order=1)
        late = self.make_image_item(first, order=5)
        early = self.make_image_item(first, order=1)
        self.make_image_item(second)

        groups = self.get_groups()
        self.assertEqual([g["id"] for g in groups], [first.pk, second.pk])
        self.assertEqual([i["id"] for i in groups[0]["items"]], [early.pk, late.pk])


class StoryGroupUpdatedAtTest(StoriesTestCase):
    def assert_touched(self, group, action):
        group.refresh_from_db()
        before = group.updated_at
        action()
        group.refresh_from_db()
        self.assertGreater(group.updated_at, before)

    def test_item_changes_touch_group(self):
        group = self.make_group()
        self.assert_touched(group, lambda: self.make_image_item(group))
        item = group.items.get()
        self.assert_touched(group, item.delete)


class StoryAdminTest(StoriesTestCase):
    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_superuser("admin", "admin@example.com", "pass")
        self.client.force_login(self.admin)

    def test_changelist_and_change_form_render(self):
        group = self.make_group()
        self.make_image_item(group)

        response = self.client.get("/admin/stories/storygroup/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "О клинике")

        response = self.client.get(f"/admin/stories/storygroup/{group.pk}/change/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Готово")
        self.assertContains(response, "9:16")

    def test_add_form_renders(self):
        response = self.client.get("/admin/stories/storygroup/add/")
        self.assertEqual(response.status_code, 200)
