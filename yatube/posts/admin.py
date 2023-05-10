from django.contrib import admin

from .models import Comment, Follow, Group, Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('pk', 'text', 'pub_date', 'author', 'group')
    list_editable = ('group',)
    search_fields = ('text',)
    list_filter = ('pub_date',)
    empty_value_display = '-пусто-'


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'description')


@admin.register(Comment)
class PostAdmin(admin.ModelAdmin):
    list_display = ('post', 'author', 'text', 'created')
    list_editable = ('text',)
    search_fields = ('text',)
    list_filter = ('created',)
    empty_value_display = '-пусто-'


@admin.register(Follow)
class PostAdmin(admin.ModelAdmin):
    list_display = ('user', 'author')
    list_filter = ('user',)
    search_fields = ('author',)
    empty_value_display = '-пусто-'
