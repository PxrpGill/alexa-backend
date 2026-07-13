from io import BytesIO

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile


def make_test_image(name='test.jpg', img_format='JPEG', mode='RGB', size=(10, 10), content_type='image/jpeg'):
    buffer = BytesIO()
    Image.new(mode, size, color='red').save(buffer, format=img_format)
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type=content_type)


class FieldFileStub:
    """Имитирует интерфейс Django FieldFile (.storage, .name, .url) без реальной модели."""

    def __init__(self, storage, name):
        self.storage = storage
        self.name = name

    def __bool__(self):
        return bool(self.name)

    @property
    def url(self):
        return self.storage.url(self.name)
