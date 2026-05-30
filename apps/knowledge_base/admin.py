from django.contrib import admin
from .models import Article, ArticleVersion

class ArticleVersionInline(admin.TabularInline):
    model = ArticleVersion
    extra = 0

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'status', 'visibility', 'author', 'created_at']
    list_filter = ['status', 'visibility', 'category']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ArticleVersionInline]