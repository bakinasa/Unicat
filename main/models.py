from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.db import models, transaction
from django.db.models import UniqueConstraint, QuerySet, Q
from django.templatetags.static import static

from main.characteristic import CharacteristicType, ComparatorStrategy, Characteristic


class User(AbstractUser):
    """
    Модель пользователя

    :param status: определяет состояние пользователя
    :param bonuses: количество бонусов

    """

    status = models.CharField(max_length=255)
    bonuses = models.IntegerField(default=0)

    def get_all_product_rate_facts(self):
        """
            :return: Все оцененные товары
        """
        return ProductRateFact.objects.filter(user=self)

    def get_all_review_rate_facts(self):
        """
            :return: Все оцененные обзоры
        """
        return ReviewRateFact.objects.filter(user=self)

    def get_all_rated_products(self):
        """
            :return: Все оцененные товары
        """
        return [fact.product for fact in self.get_all_product_rate_facts()]

    def get_all_rated_reviews(self):
        """
            :return: Все оцененные обзоры
        """
        return [fact.review for fact in self.get_all_review_rate_facts()]

    def is_store_manager(self):
        """
            :return: Является ли пользователь представителем магазина
        """
        return StoreManager.objects.filter(user_id=self)

    def get_store(self):
        """
            Если пользователь является представителем магазина

            :return: Магазин
        """
        if not self.is_store_manager():
            raise PermissionError('Пользователь не является представителем магазина')

        store_manager = StoreManager.objects.filter(user_id=self)[0]
        store = store_manager.store
        return store

    def has_already_rated(self, model_object):
        """
        Проверяет, оуенен ли уже товар пользователем

        :param model_object: проверяемый продукт
        """
        if isinstance(model_object, Product):
            return ProductRateFact.objects.filter(user=self, product=model_object).count() > 0
        if isinstance(model_object, ComparingReview):
            return ReviewRateFact.objects.filter(user=self, review=model_object).count() > 0
        return None

    def rate(self, model_object, rating):
        """
        Оценивание продукта пользователем

        :param model_object: продукт
        :param rating: оценка
        """

        model_object.user_rated += 1
        model_object.rating = ((model_object.rating * model_object.user_rated) + rating) / model_object.user_rated
        model_object.save()

        fact = ProductRateFact(user=self,
                               product=model_object,
                               rating=rating
                               ) \
        if isinstance(model_object, Product) \
        else ReviewRateFact(user=self, review=model_object, rating=rating)
        fact.save()

    def get_avatar(self):
        """
        Получение аватара пользователя

        :return: изображение
        """

        if self.useravatar_set.count() == 0:
            """
            Если аватарки нет, ставит изображение по умолчанию
            """
            return static(UserAvatar.get_default_avatar_path())
        return self.useravatar_set.first().image.url

    def product_bonuses(self):
        """
        Получение пользователем бонусов за создание карточки товара
        """
        self.bonuses += 10
        self.save()

    def review_bonuses(self):
        """
        Получение пользователем бонусов за создание сравнительного обзора
        """
        self.bonuses += 5
        self.save()


class UserAvatar(models.Model):
    """
    Модель аватарки пользователя

    :param user: какому пользователю принадлежит
    :param image: изображение

    """

    DEFAULT_AVATAR_PATH = 'imgs/profile_default_avatar.png'

    user = models.ForeignKey(to=User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='avatars')

    @staticmethod
    def get_default_avatar_path():
        """
        :return: Путь до изображения в файловой системе
        """
        return UserAvatar.DEFAULT_AVATAR_PATH

    def __str__(self):
        return self.image.url


class UserSettings(models.Model):
    """
    Модель настроек пользователя
    """
    user = models.OneToOneField(to=get_user_model(), on_delete=models.CASCADE)


class ProductCategory(models.Model):
    """
    Модель категории продукта

    :param name: наименование категории
    :param description: описание

    """
    name = models.CharField(max_length=300)
    description = models.TextField()

    def __str__(self):
        """

        :return: наименование категории
        """
        return self.name


class Product(models.Model):
    """
    Модель товара

    :param author: автор страницы товара на сайте
    :param category: тип
    :param title: наименование
    :param description: описание
    :param rating: рейтинг
    :param user_rated: оценка пользователя
    :param created_at: дата появления на сайте
    :param color: цвет(по умолчанию желтый)

    """

    author = models.ForeignKey(to=User, on_delete=models.CASCADE)
    category = models.ForeignKey(to=ProductCategory, on_delete=models.CASCADE)
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    rating = models.FloatField(default=0.0)
    user_rated = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    color = models.CharField(max_length=10, default='#FFFF00')
    views = models.IntegerField(default=0)

    def __str__(self):
        """

        :return: наименование товара
        """
        return self.title

    def get_reviews_with_product(self):
        """
        Находим все обзоры, в которых участвует данный товар
        """
        return ComparingReview.objects.filter(Q(first=self) | Q(second=self)
                                              ).order_by('-created_at')

    def get_comparable_products(self):
        """
        Находим все товары, которые сравнивались с данным в обзорах
        """
        reviews = self.get_reviews_with_product()
        comparing_products = []
        for review in reviews:
            comparing_products.append(
                {
                    'product': review.first if review.second == self else review.second,
                    'review': review
                }
            )
        return comparing_products

    @staticmethod
    def compare_products(product1: Product, product2: Product):
        """
        Метод сравнение двух товаров

        :param product1: первый продукт
        :param product2: второй продукт
        :return: результат сравнение рейтинга и характеристик товаров
        """
        if product1.category != product2.category:
            raise AttributeError('Нельзя сравнивать продукты из разных категорий')
        characteristics: QuerySet = product1.category.categorycharacteristic_set.all()
        result = {
            'first': product1,
            'second': product2,
            'comparation': {}
        }
        for characteristic in characteristics:
            comparator_cls = ComparatorStrategy.get_comparator_type(characteristic.comparator)

            p1_characteristic = product1.productcharacteristic_set.get(
                characteristic=characteristic
            )
            p1_char = Characteristic(
                p1_characteristic.characteristic.name,
                p1_characteristic.characteristic.value_type,
                p1_characteristic.value
            )

            p2_characteristic = product2.productcharacteristic_set.get(
                characteristic=characteristic
            )
            p2_char = Characteristic(
                p2_characteristic.characteristic.name,
                p2_characteristic.characteristic.value_type,
                p2_characteristic.value
            )

            if characteristic.comparator != ComparatorStrategy.RATING:
                comparator = comparator_cls(p1_char, p2_char)
            else:
                characteristic_rating = CategoryStringCharacteristicRating.objects.filter(
                    characteristic=characteristic
                ).order_by('rating')
                comparator = comparator_cls(
                    p1_char,
                    p2_char,
                    [{'value': item.value, 'rating': item.rating} for item in characteristic_rating]
                )
            compare = comparator.compare()
            result['comparation'][characteristic.name] = {
                'compare': compare
            }
        return result

    def save_product_characteristics(self, request):
        characteristics = CategoryCharacteristic.objects.filter(category=self.category)
        for index, value in enumerate(characteristics):
            char = ProductCharacteristic(characteristic=value,
                                         product=self,
                                         value=request.POST.get(f'form-{index}-value'))
            char.save()

    def is_confirmed(self):
        """
        Проверка подтверждения товара

        :return: Подтвержден ли продукт
        """
        return StoreProduct.objects.filter(product=self)

    def get_images(self) -> List[str]:
        """

        :return: изображения товара
        """
        if self.productimage_set.count() == 0:
            return [static(ProductImage.get_default_image_path())]
        return [record.image.url for record in self.productimage_set.all()]

    def get_stores(self):
        """
        Метод получения магазинов, где есть товар

        :return: магазины или None
        """

        if self.is_confirmed():
            store_product = self.is_confirmed()
            stores = [product.store for product in store_product]
            return stores
        return None

    def get_characteristic_value_by_name(self, name):
        """
        Метод получения характеристик по названию товара

        :param name: наименование товара
        :return: характеристики
        """
        return self.productcharacteristic_set.get(characteristic__name=name)


class ProductImage(models.Model):
    """
    Модель изображения товара

    :param product: наименование
    :param image: изображение

    """
    DEFAULT_IMAGE_PATH = 'imgs/src/logo_notitle.png'
    product = models.ForeignKey(to=Product, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='product_images', blank=True)

    @staticmethod
    def get_default_image_path():
        """
        :return: путь до изображения в файловой системе
        """
        return ProductImage.DEFAULT_IMAGE_PATH


class CategoryCharacteristic(models.Model):
    """
    Модель характеристик категории товаров

    :param name: наименование
    :param description: описание
    :param value_type: тип (по умолчанию: 0 - число, 1 - строка)
    :param category: тип товара
    :param сomparator: сравнение(???)

    """
    name = models.CharField(max_length=300)
    description = models.TextField()
    value_type = models.IntegerField(choices=CharacteristicType.choices,
                                     default=0)
    category = models.ForeignKey(to=ProductCategory,
                                 on_delete=models.CASCADE)
    comparator = models.IntegerField(choices=ComparatorStrategy.choices,
                                     default=ComparatorStrategy.SMALLER)

    def __str__(self):
        return f'Характеристика "{self.name}". ' \
               f'Тип: "{CharacteristicType.get_name_by_value(self.value_type)}". ' \
               f'Стратегия сравнения: "{ComparatorStrategy.get_name_by_value(self.comparator)}"'


class CategoryStringCharacteristicRating(models.Model):
    """
    Модель оценки категории товаров

    :param characteristic: характеристика товара
    :param value: описание характеристики
    :param rating: оценка

    """
    characteristic = models.ForeignKey(to=CategoryCharacteristic, on_delete=models.CASCADE)
    value = models.CharField(max_length=3000)
    rating = models.IntegerField()

    class Meta:
        constraints = [
            UniqueConstraint(fields=['characteristic', 'rating'], name='unique_votefact')
        ]

    def __str__(self):
        return f'Строковая характеристика "{self.characteristic.name}". ' \
               f'Значение: {self.value}; ' \
               f'Рейтинг: {self.rating}'

    def __repr__(self):
        return str(self)

    @staticmethod
    @transaction.atomic  # <--- Если приложение умрёт в функции -
    # мы не приведём БД в неконсистентное состояние
    def insert_new_rating(rating_list: QuerySet,
                          characteristic: CategoryCharacteristic,
                          rating: int) -> CategoryStringCharacteristicRating:
        rating_list = rating_list.filter(rating__gte=rating).order_by('-rating')
        for entry in rating_list:
            entry.rating += 1
            entry.save()
        return CategoryStringCharacteristicRating.objects.create(
            characteristic=characteristic, rating=rating
        )

    def add_new(self, characteristic: CategoryCharacteristic, rating: Optional[int] = None):
        # Если пустой рейтинг - ставим в конец
        if characteristic.value_type != CharacteristicType.str:
            raise ValueError('Only string characteristics allowed')

        rating_list = CategoryStringCharacteristicRating.objects.filter(
            characteristic=characteristic
        )

        if rating_list.count() == 0:
            return CategoryStringCharacteristicRating.objects.create(
                characteristic=characteristic, rating=1
            )

        if rating is None:
            max_rating = rating_list.order_by('-rating').first().rating
            return CategoryStringCharacteristicRating.objects.create(
                characteristic=characteristic, rating=max_rating + 1
            )

        return self.insert_new_rating(rating_list, characteristic, rating)


class ProductCharacteristic(models.Model):
    """
    Таблица характеристик товара

    :param product: продукт
    :param characteristic: характеристика типа
    :param value: описание характеристики товара(???)

    """
    product = models.ForeignKey(to=Product, on_delete=models.CASCADE, blank=True)
    characteristic = models.ForeignKey(to=CategoryCharacteristic, on_delete=models.CASCADE)
    value = models.CharField(max_length=300)

    def __str__(self):
        return f'Характеристика продукта: {self.characteristic.name}: {self.value}'

    def __repr__(self):
        return str(self)


class Store(models.Model):
    """
    Модель магазина

    :param name: название
    :param address: адресс
    :param logo: изображение логотипа

    """

    name = models.CharField(max_length=300)
    address = models.CharField(max_length=300, default='')
    logo = models.ImageField(upload_to='store_logos', default='default_store_logo.png')

    def __str__(self):
        return self.name


class StoreManager(models.Model):
    """
    Модель представителя магазина

    :param user: представитель магазина
    :param store: магазин

    """

    user = models.ForeignKey(to=User, on_delete=models.CASCADE)
    store = models.ForeignKey(to=Store, on_delete=models.CASCADE)


class StoreProduct(models.Model):
    """
    Модель товара в магазине

    :param product: товар, продающийся в магазине
    :param store: магазин

    """

    product = models.ForeignKey(to=Product, on_delete=models.CASCADE)
    store = models.ForeignKey(to=Store, on_delete=models.CASCADE)


class Application(models.Model):
    """
    Таблица данных пользователя, отправившего заявку(???)

    :param user: пользователь
    :param email: почта магазина
    :param store_name: название магазина
    :param store_address: адресс магазина
    :param status: статус (?????????)

    """

    user = models.ForeignKey(to=User, on_delete=models.CASCADE)
    email = models.EmailField()
    store_name = models.CharField(max_length=300)
    store_address = models.CharField(max_length=300)
    agreement = models.FileField(upload_to='agreements')
    status = models.CharField(max_length=300, default='under consideration')


class ComparingReview(models.Model):
    """
    Модель сравнения товаров


    :param name: наименование
    :param author: пользователь, сравнивающий товары
    :param description: описание
    :param first: первый товар
    :param second: второй товар
    :param view_count: количество просмотров
    :param rating: оценки
    :param user_rated: пользовательская оценка
    :param created_at: дата создания сравнения

    """

    name = models.CharField(max_length=300)
    author = models.ForeignKey(to=User, on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    first = models.ForeignKey(to=Product, on_delete=models.CASCADE, related_name='first')
    second = models.ForeignKey(to=Product, on_delete=models.CASCADE, related_name='second')
    view_count = models.IntegerField(default=0)
    rating = models.FloatField(default=0.0)
    user_rated = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_images(self):
        return {
            'first': self.first.get_images()[0],
            'second': self.second.get_images()[0]
        }


class ProductRateFact(models.Model):
    """
    Модель оценки товара пользователем

    :param user: оценивший пользователь
    :param product: оцененный товар
    :param rating: пользовательская оценка

    """

    user = models.ForeignKey(to=User, on_delete=models.CASCADE)
    product = models.ForeignKey(to=Product, on_delete=models.CASCADE)
    rating = models.IntegerField()


class ReviewRateFact(models.Model):
    """
    Модель обзора сравнения на товар пользователем

    :param user: создавший сравнение пользователь
    :param product: сравнение товаров
    :param rating: пользовательская оценка

    """

    user = models.ForeignKey(to=User, on_delete=models.CASCADE)
    review = models.ForeignKey(to=ComparingReview, on_delete=models.CASCADE)
    rating = models.IntegerField()


class UpdatingViews(models.Model):
    update = models.DateTimeField()
