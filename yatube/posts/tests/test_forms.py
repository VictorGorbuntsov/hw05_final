from http import HTTPStatus

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.conf import settings

from ..models import Group, Post, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class PostFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='HasNoName')
        cls.group = Group.objects.create(
            title='тест группа',
            slug='test_slug',
            description='Описание группы'
        )
        cls.create_post = Post.objects.create(
            text='тестовый текст',
            author=cls.user,
            group=cls.group,
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post_by_user(self):
        """Работа формы зарегистрирванного пользователя."""
        posts_count = Post.objects.count()
        self.assertEqual(posts_count, 1)
        form_data = {
            'text': 'Какой-то текст',
            'group': self.group.id
        }
        response = self.authorized_client.post(
            reverse('posts:create'),
            data=form_data,
            follow=True
        )

        self.assertEqual(
            response.status_code, HTTPStatus.OK)

        self.assertEqual(
            Post.objects.count(), posts_count + 1)
        post = Post.objects.first()
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.group.id, form_data['group'])
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(f'posts/{self.post_text_form["image"]}', post.image)

    def test_create_post_by_guest(self):
        """Работа формы незарегистрированного пользователя."""

        posts_count = Post.objects.count()
        post_text_form = {'text': 'Не текст'}
        response = self.client.post(
            reverse('posts:create'), data=post_text_form, follow=True)

        self.assertFalse(
            Post.objects.filter(text='Не текст').exists())
        self.assertEqual(
            response.status_code, HTTPStatus.OK)
        self.assertEqual(
            Post.objects.count(), posts_count)

    def test_post_edit_author(self):
        """Изменение поста зарегистрированным пользователем."""
        group_new = Group.objects.create(
            title='ИЗМЕНЕННОЕ НАЗВАНИЕ',
            slug='new-group',
            description='описание группы' * 5,
        )
        posts_count = Post.objects.count()
        form_data = {
            'text': 'тестовый текст',
            'group': group_new.id,
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit',
                    kwargs={'post_id': self.create_post.id}),
            data=form_data)

        edit_post = Post.objects.first()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.user, edit_post.author)
        self.assertEqual(edit_post.text, form_data['text'])
        self.assertEqual(edit_post.group.pk, form_data['group'])
        self.assertEqual(Post.objects.count(), posts_count)

    def test_post_edit_guest(self):
        """Изменение поста не зарегистрированным пользователем."""
        group_g = Group.objects.create(
            title='группа групп',
            slug='slug-slug',
            description='описание группы',
        )
        form_data = {
            'text': 'Уникальный проверочный текст',
            'group': group_g.id
        }
        response = self.client.post(
            reverse('posts:post_edit',
                    kwargs={'post_id': self.create_post.id}),
            data=form_data)
        edit_post = Post.objects.first()
        self.assertFalse(Post.objects.filter(
            text='Уникальный проверочный текст',
            group=self.group).exists())

        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(edit_post.text, form_data['text'])
        self.assertNotEqual(edit_post.group.pk, form_data['group'])
