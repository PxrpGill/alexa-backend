from django.contrib import admin

from apps.common.admin import make_image_preview

from .models import BlogCategory, BlogPost


@admin.register(BlogCategory)
class BlogCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ['preview_poster_preview', 'title', 'category', 'status', 'published_at']
    list_editable = ['status']
    list_filter = ['status', 'category']
    search_fields = ['title']
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'published_at'
    readonly_fields = [
        'created_at',
        'preview_poster_preview',
        'preview_poster_mobile_preview',
        'poster_preview',
        'poster_mobile_preview',
    ]
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'category', 'status')}),
        ('Постеры', {
            'fields': (
                ('preview_poster', 'preview_poster_preview'),
                ('preview_poster_mobile', 'preview_poster_mobile_preview'),
                ('poster', 'poster_preview'),
                ('poster_mobile', 'poster_mobile_preview'),
            ),
        }),
        ('Контент', {'fields': ('description', 'content')}),
        ('Даты', {'fields': ('published_at', 'created_at')}),
    )

    preview_poster_preview = make_image_preview(
        'preview_poster', label='Превью постера'
    )
    preview_poster_mobile_preview = make_image_preview(
        'preview_poster_mobile', label='Превью постера (моб.)'
    )
    poster_preview = make_image_preview('poster', label='Постер')
    poster_mobile_preview = make_image_preview(
        'poster_mobile', label='Постер (моб.)'
    )
