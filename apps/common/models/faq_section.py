from django.db import models
from django_ckeditor_5.fields import CKEditor5Field


class AbstractFaqFactoids(models.Model):
    question = models.TextField(verbose_name="Вопрос")
    answer = CKEditor5Field(config_name="blog_content", verbose_name="Ответ на вопрос")

    class Meta:
        abstract = True
        verbose_name = "Пара вопрос-ответ"
        verbose_name_plural = "Пара вопрос-ответ"

    def __str__(self):
        return f"{self.question} - {self.answer}"


class AbstractFaqSection(models.Model):
    title = models.CharField(
        max_length=255, verbose_name="Заголовок секции", blank=True, null=True
    )

    class Meta:
        abstract = True
        verbose_name = "Секция «Часто задаваемые вопросы»"
        verbose_name_plural = "Секция «Часто задаваемые вопросы»"

    def __str__(self):
        return self.title or "Часто задаваемые вопросы"
