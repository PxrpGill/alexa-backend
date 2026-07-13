from django.contrib import admin
from .models import BlogCategory, BlogPost


@admin.register(BlogCategory)
class BlogCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'status', 'published_at']
    list_editable = ['status']
    list_filter = ['status', 'category']
    search_fields = ['title']
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'published_at'
    readonly_fields = ['created_at']
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'category', 'status')}),
        ('Контент', {'fields': ('preview_poster', 'poster', 'description', 'content')}),
        ('Даты', {'fields': ('published_at', 'created_at')}),
    )
