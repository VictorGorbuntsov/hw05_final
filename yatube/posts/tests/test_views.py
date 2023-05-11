import tempfile
import shutil

from django.test import Client, override_settings, TestCase
from django.urls import reverse
from django import forms
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache

from ..forms import PostForm
from ..models import Comment, Follow, Post, Group, User

NUMBER_OF_PAGINATOR_POSTS = 20

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostModelTest(TestCase):

    @classmethod
    def setUpClass(cls):

        super().setUpClass()
        cls.user = User.objects.create_user(username='HasNoName')
        cls.another_user = User.objects.create(username='AnotherUser')
        cls.follow_user = User.objects.create(username='Follower')
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовый текст'
        )
        cls.another_group = Group.objects.create(
            title='Другая группа',
            slug='another_slug',
            description='Другое тестовое описание'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group,
            image=uploaded,
        )

    def check_attrs(self, response, flag=False):
        if flag:
            page_obj = response.context['post']
        else:
            page_obj = response.context['page_obj'][settings.ZERO]
        self.assertEqual(page_obj.author, self.post.author)
        self.assertEqual(page_obj.group, self.post.group)
        self.assertEqual(page_obj.id, self.post.id)
        self.assertEqual(page_obj.text, self.post.text)
        self.assertEqual(page_obj.pub_date, self.post.pub_date)
        self.assertEqual(page_obj.image, self.post.image)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

        self.follow_client = Client()
        self.follow_client.force_login(self.follow_user)

    def test_index_context(self):
        """Шаблон Index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))

        self.check_attrs(response)

    def test_group_list_context(self):
        """Проверка Group list использует правильные данные в контекст."""
        response = self.authorized_client.get(
            reverse('posts:group_list', args=(self.group.slug,)))
        group_test = response.context['group']
        self.assertIn('page_obj', response.context)
        self.assertEqual(group_test, self.group)
        self.check_attrs(response)

    def test_profile_context(self):
        """Проверка profile использует правильный контекст."""
        response = self.authorized_client.get(
            reverse('posts:profile', args=(self.user.username,)))
        self.assertIn('author', response.context)
        author = response.context.get('author')
        self.assertEqual(author, self.user)
        self.check_attrs(response)

    def test_post_detail_context(self):
        """Проверка Post detail использует правильный контекст."""
        response = self.authorized_client.get(reverse(
            'posts:post_detail', args=(self.post.id,)))

        self.check_attrs(response, flag=True)

    def test_post_edit_context(self):
        """Post create page with post_edit использует правильный контекст."""
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        urls = (
            ('posts:create', None),
            ('posts:post_edit', (self.post.id,)),
        )
        for url, slug in urls:
            reverse_name = reverse(url, args=slug)
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertIn('form', response.context)
                self.assertIsInstance(response.context['form'], PostForm)
                for value, expected in form_fields.items():
                    with self.subTest(value=value):
                        form_field = response.context.get(
                            'form').fields.get(value)
                        self.assertIsInstance(form_field, expected)

    def test_post_didnot_fall_into_wrong_group(self):
        """Тест на то, что пост не попал не в ту группу."""
        group_not_group = Group.objects.create(
            title='Тестовая негруппа',
            slug='aaa',
            description='Тестовое описание',
        )

        response = self.client.get(
            reverse('posts:group_list', args=(self.group.slug,)))
        page_obj = response.context['page_obj'][settings.ZERO]
        self.assertNotEqual(group_not_group, page_obj.group)
        self.assertEqual(page_obj.group, self.group)

    def test_index_cache(self):
        """Тест кэша"""
        cache_content = self.client.get(reverse('posts:index')).content
        Post.objects.create(
            text='Текст для проверки кэша',
            author=self.user
        )
        cache_before_20sec = self.client.get(reverse('posts:index')).content
        self.assertEqual(cache_content, cache_before_20sec)
        cache.clear()
        cache_after_20sec = self.client.get(reverse('posts:index')).content
        self.assertNotEqual(cache_content, cache_after_20sec)

    def test_authorized_user_follow(self):
        """Авторизированный пользователь может ПОДПИСАТЬСЯ на автора"""
        fol_num_before = Follow.objects.count()
        self.authorized_client.get(
            reverse('posts:profile_follow',
                    args=(self.another_user.username,)))
        fol_num_after = Follow.objects.count()
        self.assertEqual(fol_num_after, fol_num_before + settings.NUMBER_ONE)
        follow = Follow.objects.filter(
            user=self.user, author=self.another_user).first()
        self.assertEqual(follow.user, self.user)
        self.assertEqual(follow.author, self.another_user)

    def test_authorized_user_unfollow(self):
        """Авторизированный пользователь может ОТПИСАТЬСЯ от автора"""
        Follow.objects.create(user=self.user, author=self.another_user)
        self.authorized_client.get(
            reverse('posts:profile_unfollow',
                    args=(self.another_user.username,)))

    # def test_new_post_follower(self):
    #     """Пост появляется в ленте подписчика"""
    #     Follow.objects.create(user=self.user, author=self.another_user)
    #     response = self.authorized_client.get(
    #         reverse('posts:follow_index'))
    #     self.assertEqual(self.post,
    #                      response.context[0])

     # def test_new_post_not_follower(self):
     #     """Пост НЕ появляется в ленте не подписчика"""
     #     response = self.follow_client.get(
     #         reverse('posts:follow_index'))
     #     self.assertNotIn(self.post, response.context['page_obj'])


class PaginatorViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = User.objects.create(username='HasNoName')
        cls.follow_user = User.objects.create(username='Follower')

        Follow.objects.create(
            user=cls.follow_user,
            author=cls.user,
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )

        list_of_posts = []

        for page in range(NUMBER_OF_PAGINATOR_POSTS):
            list_of_posts.append(
                Post(
                    text=f'Test text №{page}',
                    author=cls.user,
                    group=cls.group,
                ))
        Post.objects.bulk_create(list_of_posts)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_paginator_first_page(self):
        """Проверка корректной работы paginator."""

        list_of_check_page = (
            ('posts:index', None),
            ('posts:profile', (self.user.username,)),
            ('posts:group_list', (self.group.slug,)),
        )
        list_of_paginator_page = (
            ('?page=1', settings.POSTS_ON_PAGE),
            ('?page=2', settings.POSTS_ON_PAGE)
        )

        for name, args in list_of_check_page:
            with self.subTest(name=name):
                for page, quantity in list_of_paginator_page:
                    with self.subTest(page=page, quantity=quantity):
                        response = self.authorized_client.get(reverse(name, args=args)
                                                   + page)
                        self.assertEqual(
                            len(response.context['page_obj']),
                            quantity)
