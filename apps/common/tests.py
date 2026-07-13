import os
import shutil
import tempfile
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.test import TestCase
from PIL import Image

from apps.common.images import generate_image_variants
from apps.common.test_utils import FieldFileStub, make_test_image


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
