from http import HTTPStatus

from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post, User


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='HasNoName')
        cls.user1 = User.objects.create_user(username='user1')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовый текст'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group
        )

    def setUp(self):
        self.not_author = Client()
        self.not_author.force_login(self.user1)
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.reverse_names = (
            ('posts:index', None),
            ('posts:group_list', (self.group.slug,)),
            ('posts:profile', (self.user.username,)),
            ('posts:post_detail', (self.post.id,)),
            ('posts:post_edit', (self.post.id,)),
            ('posts:create', None),
            ('posts:follow_index', None),
            ('posts:profile_follow', (self.user.username,)),
            ('posts:profile_unfollow', (self.user.username,)),
            ('posts:add_comment', (self.post.id,)),
        )

    def test_for_matching_reverse_with_hardcore(self):
        '''тест проверки соответствия, что прямые - хардкод ссылки
        равны полученным по reverse(name)'''
        reverse_for_url = (
            ('posts:index', None, '/'),
            ('posts:group_list',
             (self.group.slug,),
             f'/group/{self.group.slug}/'
             ),
            ('posts:profile',
             (self.user.username,),
             f'/profile/{self.user.username}/'
             ),
            ('posts:post_detail',
             (self.post.id,),
             f'/posts/{self.post.id}/'
             ),
            ('posts:post_edit',
             (self.post.id,),
             f'/posts/{self.post.id}/edit/'
             ),
            ('posts:create', None, '/create/'),
            ('posts:add_comment',
             (self.post.id,),
             f'/posts/{self.post.id}/comment/',
             ),
            ('posts:follow_index', None, '/follow/'),
            ('posts:profile_follow',
             (self.user.username,),
             f'/profile/{self.user.username}/follow/',
             ),
            ('posts:profile_unfollow',
             (self.user.username,),
             f'/profile/{self.user.username}/unfollow/',
             ),
        )
        for name, args, url in reverse_for_url:
            with self.subTest(name=name):
                reverse_url = reverse(name, args=args)
                self.assertEqual(reverse_url, url)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = (
            ('posts:index', None, 'posts/index.html'),
            ('posts:group_list', (self.group.slug,), 'posts/group_list.html'),
            ('posts:profile', (self.post.author,), 'posts/profile.html'),
            ('posts:post_detail', (self.post.id,), 'posts/post_detail.html'),
            ('posts:post_edit', (self.post.id,), 'posts/create_post.html'),
            ('posts:create', None, 'posts/create_post.html'),
            ('posts:follow_index', None, 'posts/follow.html'),
        )
        for name, args, template in templates_url_names:
            with self.subTest(name=name):
                response = self.authorized_client.get(reverse(name, args=args))
                self.assertTemplateUsed(response, template)

    def test_urls_access_anonim(self):
        """Доступность URL адреса для анонимного пользователя"""
        reverse_for_url = ('posts:post_edit', 'posts:create')
        for name, args in self.reverse_names:
            with self.subTest(name=name):
                response = self.client.get(reverse(name, args=args),
                                           follow=True)
                if name in reverse_for_url:
                    url_one = reverse('users:login')
                    url_two = reverse(name, args=args)
                    self.assertRedirects(response, (
                        f'{url_one}?next={url_two}'))
                else:
                    self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_author(self):
        """Доступность URL адреса автору поста"""
        for url, args in self.reverse_names:
            with self.subTest(url=url):
                response = self.authorized_client.get(reverse(url, args=args),
                                                      follow=True)
                if url == 'posts:profile_follow':
                    self.assertRedirects(response, reverse('posts:profile',
                                                           args=args))
                elif url == 'posts:profile_unfollow':
                    self.assertEqual(response.status_code,
                                     HTTPStatus.NOT_FOUND)
                elif url == 'posts:add_comment':
                    self.assertRedirects(response, reverse('posts:post_detail',
                                                           args=args))
                else:
                    self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_404_url_locations(self):
        """Не доступная страница"""
        response = self.client.get('/404/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_urls_not_author(self):
        """Доступность URL адреса не автору поста"""
        for name, args in self.reverse_names:
            with self.subTest(name=name):
                response = self.not_author.get(reverse(name, args=args),
                                               follow=True)
                if name == 'posts:post_edit':
                    self.assertRedirects(response, reverse('posts:post_detail',
                                                           args=args))
                else:
                    self.assertEqual(response.status_code, HTTPStatus.OK)
