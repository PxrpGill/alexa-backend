from django.db import models
from django_ckeditor_5.fields import CKEditor5Field


class BlogCategory(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')
    slug = models.SlugField(unique=True, verbose_name='Slug')

    class Meta:
        verbose_name = 'Категория блога'
        verbose_name_plural = 'Категории блога'

    def __str__(self):
        return self.name


class BlogPost(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Черновик'
        PUBLISHED = 'published', 'Опубликовано'

    title = models.CharField(max_length=500, verbose_name='Заголовок')
    slug = models.SlugField(unique=True, verbose_name='Slug')
    category = models.ForeignKey(
        BlogCategory, on_delete=models.PROTECT,
        related_name='posts', verbose_name='Категория',
    )
    cover = models.ImageField(upload_to='blog/', blank=True, verbose_name='Обложка')
    excerpt = models.TextField(verbose_name='Краткое описание')
    content = CKEditor5Field(config_name='default', verbose_name='Контент')
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.DRAFT, verbose_name='Статус',
    )
    published_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата публикации')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')

    class Meta:
        verbose_name = 'Статья'
        verbose_name_plural = 'Статьи'
        ordering = ['-published_at']

    def __str__(self):
        return self.title
