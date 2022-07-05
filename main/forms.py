from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Div
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse

from main.models import User, Product, ProductImage, UserAvatar, \
    ComparingReview, CategoryCharacteristic, Application, ProductCharacteristic


class RegistrationForm(UserCreationForm):
    """
    Форма регистрации пользователя

    :param email: электронный адрес
    :param agreement_checked: проверка подтверждения принятия условий соглашения
    :type agreement_checked: BooleanField
    """

    email = forms.EmailField(required=True)
    agreement_checked = forms.BooleanField(
        label='Я принимаю условия соглашения',
        widget=forms.CheckboxInput()
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')


class CreateVotingForm(forms.Form):
    """
    ???????
    """
    title = forms.CharField(
        label='Название голосования',
        required=True
    )
    description = forms.CharField(
        label='Описание голосования',
        required=True
    )
    type = forms.IntegerField(
        label='Тип голосования',
        min_value=1,
        max_value=3,
        required=True
    )


class EditVotingForm(forms.Form):
    title = forms.CharField(
        label='Название голосования',
        required=True
    )
    description = forms.CharField(
        label='Описание голосования',
        required=True
    )


class EditProfileForm(forms.Form):
    """
    Заполнение профиля пользователя

    :param username: имя пользователя на сайте
    :param first_name: имя пользователя
    :param last_name: фамилия пользователя
    :param email: электронный адрес пользователя
    """
    username = forms.CharField(
        label='Имя пользователя',
        required=True
    )
    first_name = forms.CharField(
        label='first_name',
        required=True
    )
    last_name = forms.CharField(
        label='last_name',
        required=True
    )
    email = forms.CharField(
        label='Email',
        required=True
    )


class UploadUserAvatarForm(forms.ModelForm):
    """
    Форма пользовательского аватара

    """
    class Meta:
        model = UserAvatar
        fields = ['user', 'image']
        widgets = {'user': forms.HiddenInput()}
        labels = {'image': 'Фотография профиля'}


class ProductAddingForm(forms.ModelForm):
    """
    Добавление нового продукта

    """
    class Meta:
        model = Product
        fields = ['category', 'title', 'color']
        labels = {'category': 'Категория',
                  'title': 'Название',
                  'color': 'Цвет'}
        widgets = {
            'category': forms.Select(attrs={'id': 'category_selector'}),
            'color': forms.TextInput(attrs={'type': 'color'}),
        }


class ProductEditForm(forms.ModelForm):
    """
    Редактирование формы продукта
    """
    class Meta:
        model = Product
        fields = ['category', 'title', 'color', 'description']
        labels = {'category': 'Категория',
                  'title': 'Название',
                  'color': 'Цвет',
                  'description': 'Описание'}
        widgets = {
            'color': forms.TextInput(attrs={'type': 'color'}),
        }


class ProductImageForm(forms.ModelForm):
    """
    Форма картинки продукта
    """
    class Meta:
        model = ProductImage
        fields = ['product', 'image']
        widgets = {
            'product': forms.HiddenInput(),
            'image': forms.FileInput(attrs={'multiple': True, 'id': 'file-input'})
        }
        labels = {'image': 'Выберите фотографию'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""


class ApplicationForm(forms.ModelForm):

    class Meta:
        model = Application
        fields = ['user', 'email', 'store_name', 'store_address', 'agreement']
        labels = {'store_name': 'Название магазина', 'store_address': 'Адрес магазина',
                  'agreement': 'Соглашение на предоставление бонусной программы'}
        widgets = {'user': forms.HiddenInput(), 'email': forms.HiddenInput()}


class ComparingReviewForm(forms.ModelForm):
    """
    Форма сравнительного обзора

    """
    class Meta:
        model = ComparingReview
        fields = ['name', 'author', 'description', 'first', 'second']
        widgets = {'author': forms.HiddenInput()}
        labels = {
            'name': 'Название',
            'description': 'Описание',
            'first': 'Первый товар',
            'second': 'Второй товар'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'first' in self.initial.keys():  # Если форма создаётся для отображения на сайте
            product = self.initial['first']
            self.fields["second"].queryset = Product.objects.filter(category=product.category
                                                                    ).exclude(id=product.id)


class CategoryCharacteristicForm(forms.ModelForm):
    """
    Характеристики категории товаров

    """
    class Meta:
        model = CategoryCharacteristic
        fields = ['name', 'description', 'category', 'value_type', 'comparator']
        widgets = {
            'category': forms.HiddenInput(),
            'name': forms.TextInput(),
            'description': forms.TextInput()
        }

    def __init__(self, cat_id, char_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_action = reverse('category_characteristics_edit',
                                          kwargs={'category_id': cat_id, 'char_id': char_id})
        self.helper.layout = Layout(
            Div(
                Div('name', css_class='col'),
                Div('description', css_class='col'),
                'category',
                Div('value_type', css_class='col'),
                Div('comparator', css_class='col'),
                Div(Submit('submit', 'Submit', css_class='btn btn-primary'), css_class='col'),
                css_class='row',
            ),
        )


class ProductCharacteristicForm(forms.ModelForm):
    """
    Характеристика продукта
    """
    class Meta:
        model = ProductCharacteristic
        fields = ['product', 'characteristic', 'value']
        widgets = {
            'product': forms.HiddenInput(),
            'characteristic': forms.TextInput(attrs={'disabled': ''}),
        }
