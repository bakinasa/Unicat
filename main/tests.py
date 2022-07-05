"""
Тесты сайта, направленные на выявление и исправление багов и других логических ошибок
"""

from django.test import TestCase, Client, tag
from django.urls import reverse

from main.models import User


class UserTestCase(TestCase):
    """
    Класс тестов пользователей

    """
    fixtures = [
        'users.json',
        'categories.json',
        'products.json',
        'product_rate_facts.json'
    ]

    def setUp(self) -> None:
        """
        Регистрация тестовых пользователей:
        vasya и petya

        """
        self.vasya = User.objects.get(id=1)
        self.petya = User.objects.get(id=2)

    def test_all_product_rate_facts(self):
        """
        Проверка факта оценки товаров пользователем vasya

        """
        result = self.vasya.get_all_product_rate_facts()
        self.assertEqual(result.count(), 2)

    def test_all_product_rate_facts_zero(self):
        """
        Проверка факта оценки товара пользователем petya

        """
        result = self.petya.get_all_product_rate_facts()
        self.assertEqual(result.count(), 0)

    def test_get_all_rated_products(self):
        """
        Проверка получения всех оцененных товаров пользователем vasya

        """
        result = self.vasya.get_all_rated_products()
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].title, 'fiio fd3 pro')
        self.assertEqual(result[1].title, 'kz zsn pro x')

    def test_get_all_rated_products_zero(self):
        """
        Проверка получения всех оцененных товаров пользователем petya

        """
        result = self.petya.get_all_rated_products()
        self.assertEqual(len(result), 0)


class ProfileViewTestCase(TestCase):
    """
    Класс тестов профиля
    """
    fixtures = [
        'users.json',
        'categories.json',
        'products.json',
        'product_rate_facts.json',
        'stores.json',
        'store_managers.json'
    ]

    def setUp(self) -> None:
        """
        Создание клиента
        """
        self.client = Client()

    def tests_profile_without_login(self):
        """
        Проверка получения профиля без логина

        """
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 302)

    def test_profile_as_superuser(self):
        """
        Проверка профиля админа

        """
        vasya = User.objects.get(username='vasya')
        self.client.force_login(vasya)
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['ratefact_count'], 2)
        self.assertFalse('products' in response.context)

    def test_profile_as_store_manager(self):
        """
        Проверка профиля представителя магазина

        """
        sergey = User.objects.get(username='sergey')
        self.client.force_login(sergey)
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['ratefact_count'], 0)
        self.assertTrue('products' in response.context)


class ProductViewTestCase(TestCase):
    """
    Класс тестов представлений на сайте
    """
    fixtures = [
        'users.json',
        'categories.json',
        'products.json',
        'product_rate_facts.json',
        'product_images.json',
        'product_characteristics.json',
        'category_characteristics.json'
    ]

    def setUp(self) -> None:
        self.client = Client()

    @tag('future')
    def test_check_edit_without_login(self):
        """
        Проверка возмжности дополнения данных продукта без логина

        """
        response = self.client.get(reverse('product_page', kwargs={'product_id': 1}))
        self.assertNotContains(response, 'Редактировать', status_code=200)

    def test_check_edit_as_default_user(self):
        """
        Проверка редактирования пользователя по умолчанию

        """
        vasya = User.objects.get(username='vasya')
        self.client.force_login(vasya)
        response = self.client.get(reverse('product_page', kwargs={'product_id': 1}))
        self.assertContains(response, 'Редактировать', status_code=200)

    def test_product_no_images(self):
        """
        Проверка отображения изображения по умолчанию товара

        """
        response = self.client.get(reverse('product_page', kwargs={'product_id': 1}))
        self.assertEqual(response.context['images'], ['/static/imgs/src/logo_notitle.png'])

    def test_product_has_one_image(self):
        """
        Проверка отображения единственного изображения у товара

        """
        response = self.client.get(reverse('product_page', kwargs={'product_id': 2}))
        self.assertEqual(len(response.context['images']), 1)
        self.assertNotContains(response, 'imgs/src/logo_notitle.png', status_code=200)

    def test_product_has_more_images(self):
        """
        Проверка отображения изображений товара

        """
        response = self.client.get(reverse('product_page', kwargs={'product_id': 3}))
        self.assertEqual(len(response.context['images']), 2)
        self.assertNotContains(response, 'imgs/src/logo_notitle.png', status_code=200)

    def test_product_view_characteristic(self):
        """
        Проверка отображения характеристик товара

        """
        response = self.client.get(reverse('product_page', kwargs={'product_id': 2}))
        self.assertContains(response, 'Характеристика', status_code=200)

    @tag('future')
    def test_product_view_no_characteristic(self):
        """
        Проверка отображения товара без характеристик:
            Если у товара нет характеристик - таблица с характеристиками не должна отображаться
        """
        response = self.client.get(reverse('product_page', kwargs={'product_id': 1}))
        self.assertNotContains(response, 'Характеристика', status_code=200)

    def test_authorized_user_rates(self):
        """
        Проверка оценки товара зарегестрированным пользователем

        """
        petya = User.objects.get(username='petya')
        self.client.force_login(petya)
        response = self.client.post('/catalog/1/', {'rating': '5'})
        messages = list(response.context['messages'])
        self.assertEqual(str(messages[0]), 'Благодарим за оценку!')
        self.assertEqual(response.context['product'].user_rated, 1)

    def test_no_authorized_user_rates(self):
        """
        Проверка оценки товара незарегестрированным пользователем

        """
        response = self.client.post(reverse('product_page', kwargs={'product_id': 1}),
                                    {'rating': '5'})
        messages = list(response.context['messages'])
        self.assertEqual(str(messages[0]), 'Зарегистрируйтесь, чтобы оставить отзыв!!!')

    @tag('future')
    def test_category_badge_on_product_page(self):
        """
        Проверка отображения знака категории

        """
        response = self.client.get(reverse('product_page', kwargs={'product_id': 2}))
        self.assertContains(response, 'Категория', status_code=200)
        self.assertContains(response, 'Наушники', status_code=200)
