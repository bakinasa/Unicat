from datetime import datetime

from django import forms
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.forms import formset_factory
from django.http import Http404
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.timezone import get_current_timezone

from main.forms import EditProfileForm, ProductEditForm, ProductImageForm, UploadUserAvatarForm, \
    ProductAddingForm, CategoryCharacteristicForm, ComparingReviewForm, ApplicationForm, \
    ProductCharacteristicForm
from main.forms import RegistrationForm
from main.models import User, ComparingReview, Product, UserAvatar, ProductRateFact, \
    ProductCategory, CategoryCharacteristic, StoreManager, StoreProduct, Application, \
    Store, ProductImage, UpdatingViews


def get_menu_context():
    """
    Функция получения контекста меню
    """
    return [
        {'url_name': 'index', 'name': 'Главная'},
    ]


def is_ajax(request):
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'


def get_base_context(pagename, request):
    """
    Функция получения базового контекста страницы

    :return: словарь - контекст страницы
    """
    context = {
        'app': Application.objects.filter(status='under consideration').count(),
        'apps': Application.objects.filter(status='under consideration'),
        'pagename': pagename,
        'menu': get_menu_context()
    }
    if request.user.is_authenticated:
        context['avatar'] = request.user.get_avatar()
    return context


def index_page(request):
    """
    Главная страница

    :param request: детали запроса
    :return: главная страница
    """
    if request.user.is_authenticated:
        return redirect('catalog')
    context = get_base_context('Главная', request)
    return render(request, 'pages/index.html', context)


@login_required
def profile_page(request):
    """
    Получение страницы профиля пользователя

    :param request: запрос
    :return: страница пользователя

    'menu': меню
    'pagename': название страницы
    'votings_count': количество сравнений товаров
    'ratefact_count': количество оценок товаров
    'avatar': аватар
    'products': все оцененные товары
    """
    context = {
        'menu': get_menu_context(),
        'pagename': 'Профиль',
        'votings_count': ComparingReview.objects.filter(author=request.user).count(),
        'ratefact_count': request.user.get_all_product_rate_facts().count(),
        'avatar': request.user.get_avatar(),
    }

    if request.user.is_store_manager():
        context['products'] = Product.objects.all().order_by('rating')

    return render(request, 'pages/profile/profile.html', context)


@login_required
def profile_edit_page(request, user_id):
    """
    Метод редактирования страницы пользователя

    :param request: детали запроса
    :param user_id: id пользователя
    :return: страница пользователя
    """

    user = get_object_or_404(User, id=user_id)
    context = {
        'menu': get_menu_context(),
        'pagename': ' Редактирование профиля',
        'votings_count': ComparingReview.objects.filter(author=request.user).count(),
        'ratefact_count': ProductRateFact.objects.filter(user=request.user).count(),
        'form': EditProfileForm(),
        'user': get_object_or_404(User, id=user_id),
        'avatar': request.user.get_avatar()
    }
    context['form2'] = UploadUserAvatarForm(initial={
        'user': context['user']
    })
    if request.method == "POST":
        form = EditProfileForm(request.POST)
        form2 = UploadUserAvatarForm(request.POST, request.FILES)

        if form.is_valid():
            user.username = form.cleaned_data['username']
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data['email']
            user.save()
            messages.success(request, 'Изменения сохранены', 'alert-success')

        if form2.is_valid():
            try:
                avatar = UserAvatar.objects.filter(user=request.user)[0]
                avatar.user = form2.cleaned_data['user']
                avatar.image = form2.cleaned_data['image']
                avatar.save()
            except IndexError:
                form2.save()
            messages.success(request, 'Аватар сохранен', 'alert-success')
        return redirect('profile')
    return render(request, 'pages/profile/profile_edit.html', context)


def registration_page(request):
    """
    Регистрация пользователя

    :param request: запрос
    :return: страница регестрации
    """
    if request.user.is_authenticated:
        messages.error(request, "Залогиненный пользователь не может регистрироваться",
                       extra_tags='alert-danger')
    context = get_base_context('Регистрация', request)
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.refresh_from_db()
            user.save()
            raw_pass = form.cleaned_data.get('password1')
            avatar = UserAvatar(
                user=user,
                image="https://html5book.ru/wp-content/uploads/2016/10/profile-image.png")
            avatar.save()
            user = authenticate(username=user.username,
                                password=raw_pass,
                                first_name=user.first_name,
                                last_name=user.last_name)
            login(request, user)
            messages.info(request,
                          'Заполните специальную форму, если Вы - представитель магазина',
                          'alert-info')
            return redirect(reverse('index'))
    else:
        form = RegistrationForm()
    context['form'] = form
    return render(request, 'registration/registration.html', context)


@login_required
def registration_store_manager_page(request):
    """
    Страница регестрации представителя магазина

    :param request: запрос
    :return: страница регестрации представителя магазина
    """

    context = get_base_context('Регистрация представителя магазина', request)
    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Заявка отправлена', 'alert-success')
            return redirect(reverse('index'))
        messages.error(request, 'Ошибка создания заявки', 'alert-danger')
    else:
        form = ApplicationForm(initial={'user': request.user, 'email': request.user.email})
    context['form'] = form
    return render(request, 'registration/store_manager_new.html', context)


def comparing_review_page(request, rev_id):
    review = get_object_or_404(ComparingReview, id=rev_id)
    compare_data = Product.compare_products(review.first, review.second)
    table = []
    for key, value in compare_data['comparation'].items():
        table.append(
            {
                'characteristic': key,
                'first_value': review.first.get_characteristic_value_by_name(key).value,
                'second_value': review.second.get_characteristic_value_by_name(key).value,
                'compare': value['compare'].cmp
            }
        )
    context = get_base_context("Обзор", request)
    context['review'] = review
    context['comparing_table'] = table

    if request.method == "POST" and request.POST['rating']:
        if request.user.is_authenticated:
            if request.user.has_already_rated(review):
                messages.warning(request, 'Вы уже оценили обзор', 'alert-warning')
            else:
                request.user.rate(review, int(request.POST['rating']))
                messages.success(request, 'Благодарим за оценку!', 'alert-success')
        else:
            messages.warning(request, 'Зарегистрируйтесь, чтобы оставить отзыв!!!', 'alert-warning')

    return render(request, 'pages/comparing_review/comparing_review.html', context)


@login_required
def product_add_page(request):
    """
    Страница добавления нового товара

    :param request: запрос
    :return: страница добавления товара
    """

    context = get_base_context('Добавление нового товара', request)
    context['form'] = ProductAddingForm()
    context['image_form'] = ProductImageForm(initial={
        'product': 1
    })

    if request.method == "POST":
        form = ProductAddingForm(request.POST)
        product = None

        if form.is_valid():
            product = form.save(commit=False)
            product.author = request.user
            product.save()
            context['product'] = product
            request.user.product_bonuses()
            messages.success(request, 'Товар успешно создан', 'alert-success')
        else:
            messages.error(request, 'Ошибка создания товара', 'alert-danger')

        image_form = ProductImageForm(request.POST, request.FILES)

        if image_form.is_valid():
            if image_form.cleaned_data['image'] is not None:
                image = image_form.save(commit=False)
                image.product = product
                image.save()
        else:
            messages.error(request, 'Ошибка загрузки изображения', 'alert-danger')

        product.save_product_characteristics(request)

        return redirect(reverse('product_page', kwargs={'product_id': product.id}))

    return render(request, 'pages/product/add_product.html', context)


def catalog_page(request):
    context = get_base_context('Каталог товаров', request)
    products = Product.objects.all()
    context['categories'] = ProductCategory.objects.all()

    if 'category' in request.GET:
        # фильтруем по категории
        category_id = request.GET.get('category')
        if category_id != '-1':  # -1 это "все категории"
            try:
                category = get_object_or_404(ProductCategory, id=int(category_id))
                context['filter_category'] = category
                products = products.filter(category=category)
            except ValueError as value_error:
                raise Http404 from value_error

    if 'sort_filter' in request.GET:
        sort_filter = request.GET.get('sort_filter')
        products = products.order_by('-'+sort_filter)
        context['sort_filter'] = sort_filter
    else:
        products = products.order_by('-rating')

    context['products'] = products
    return render(request, 'pages/catalog/catalog_page.html', context)


def search_results_page(request):
    context = get_base_context('Результаты поиска', request)
    context['products'] = Product.objects.filter(title__icontains=request.GET.get('title', '')
                                                 ).order_by('rating')
    return render(request, 'pages/catalog/catalog_page.html', context)


def review_search_results_page(request):
    context = get_base_context('Результаты поиска', request)
    context['reviews'] = ComparingReview.objects.filter(name__icontains=request.GET.get('title',
                                                                                        ''))
    context['categories'] = ProductCategory.objects.all()
    if 'category' in request.GET:
        category_id = request.GET.get('category')
        try:
            category = get_object_or_404(ProductCategory, id=int(category_id))
            context['filter_category'] = category
            reviews = ComparingReview.objects.filter(first__category=category)
        except ValueError as value_error:
            raise Http404 from value_error
        context['reviews'] = reviews
    return render(request, 'pages/catalog/catalog_reviews.html', context)


def product_page(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if UpdatingViews.objects.all().count() == 0:
        update = UpdatingViews(update=datetime.now(tz=get_current_timezone()))
        update.id = 1
        update.save()
    update = get_object_or_404(UpdatingViews, id=1)
    if (update.update.day != datetime.now(tz=get_current_timezone()).day) or (update.update.month != datetime.now(tz=get_current_timezone()).month):
        for p in Product.objects.all():
            p.views = 0
            p.save()
        update.update = datetime.now(tz=get_current_timezone())
        update.save()
        product.views = 0
    product.views += 1
    product.save()
    context = get_base_context("Товар: " + product.title, request)
    if product.views % 10 == 1:
        context['views_type'] = 1
    elif 2 <= product.views % 10 <= 4:
        context['views_type'] = 2
    elif product.views % 10 > 4 or product.views % 10 == 0:
        context['views_type'] = 3
    context['product'] = product
    context['images'] = product.get_images()
    context['characteristics'] = product.productcharacteristic_set.all()
    context['reviews'] = product.get_comparable_products()[:5]
    context['reviews_url'] = reverse('catalog_reviews') + f'?product={product.id}'
    if product.is_confirmed():
        context['stores'] = product.get_stores()

    if request.method == "POST" and request.POST['rating']:
        if request.user.is_authenticated:
            if request.user.has_already_rated(product):
                messages.warning(request, 'Вы уже оценили товар', 'alert-warning')
            else:
                request.user.rate(product, int(request.POST['rating']))
                messages.success(request, 'Благодарим за оценку!', 'alert-success')
        else:
            messages.warning(request, 'Зарегистрируйтесь, чтобы оставить отзыв!!!', 'alert-warning')
    return render(request, 'pages/product/product_page.html', context)


@login_required
def product_edit_page(request, product_id):
    context = get_base_context('Каталог товаров', request)
    product = get_object_or_404(Product, id=product_id)
    context['product'] = product
    context['form'] = ProductEditForm(instance=product)
    context['images'] = product.get_images()
    context['add_image_form'] = ProductImageForm(initial={
        'product': product
    })

    if request.method == "POST":
        product = get_object_or_404(Product, id=product_id)
        form = ProductEditForm(request.POST)
        if form.is_valid():
            product.title = form.cleaned_data['title']
            product.category = form.cleaned_data['category']
            product.color = form.cleaned_data['color']
            product.description = form.cleaned_data['description']
            product.save()
            messages.success(request, 'Изменения сохранены', 'alert-success')
            return redirect(reverse('product_page', kwargs={'product_id': product.id}))

    return render(request, 'pages/product/product_edit_page.html', context)


def product_add_image(request):
    """ Function for ajax to add image for product """
    if request.method != 'POST' or not is_ajax(request):
        raise PermissionError('Only for JSON ajax-requests.')

    form = ProductImageForm(request.POST, request.FILES)
    response = {
        'success': True,
        'error': None,
    }
    if 'image' in request.FILES:
        if form.is_valid() and request.FILES['image'].size <= 5242880:  # 5242880 = 5MB
            image_record = form.save()
            response['image_id'] = image_record.id
            return JsonResponse(data=response)
        else:
            response['success'] = False
            response['error'] = 'Файл не является изображением или больше 5Мб'
            return JsonResponse(response, status=415)
    else:
        response['success'] = False
        response['error'] = 'Изображение не было отправлено'
        return JsonResponse(response, status=400)


def product_remove_image(request):
    """ Function for ajax to remove product image """
    if not is_ajax(request):
        raise PermissionError('Only for JSON ajax-requests.')

    product_id = request.POST.get('product')
    image_id = request.POST.get('image_id')
    product = get_object_or_404(Product, id=product_id)
    image_record = get_object_or_404(ProductImage, id=image_id)

    # Проверяем есть ли это изображение у данного продукта
    if image_record in product.productimage_set.all():
        image_record.delete()
        response = {
            'success': True,
            'error': None,
            'image_id': image_id
        }
        return JsonResponse(data=response)

    response = {'success': False, 'error': 'Не получилось удалить изображение'}
    return JsonResponse(response, status=400)


def product_delete(request, product_id):
    if request.user.is_staff:
        product = get_object_or_404(Product, id=product_id)
        product.delete()
        messages.warning(request, 'Продукт удалён', 'alert-warning')
    return redirect(reverse('catalog'))


def product_verify(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    store_product = StoreProduct(
        product=product,
        store=request.user.get_store()
    )
    store_product.save()
    messages.success(request, 'Продукт верифицирован', 'alert-success')
    return redirect(reverse('catalog'))


def product_cancel_verification(request, product_id):
    store_product = get_object_or_404(StoreProduct, product=product_id)
    store_product.delete()
    messages.warning(request, 'Верификация отменена', 'alert-warning')
    return redirect(reverse('catalog'))


@login_required
def applications_page(request):
    if request.user.is_staff:
        context = get_base_context('Заявки', request)
        context['avatar'] = request.user.get_avatar()
        context['apps'] = Application.objects.filter(status='under consideration')
    else:
        raise PermissionError('К сожалению, вам отказано в доступе к данной странице')
    return render(request, 'pages/moderation/applications.html', context)


def application_accept(request, app_id):
    application = get_object_or_404(Application, id=app_id)

    if not Store.objects.filter(name=application.store_name, address=application.store_address):
        store = Store(name=application.store_name)
        store.save()
    else:
        store = Store.objects.filter(name=application.store_name,
                                     address=application.store_address)[0]

    store_manager = StoreManager(store=store, user=application.user)
    store_manager.save()

    application.status = 'accepted'
    application.save()

    messages.success(request, 'Заявка одобрена', 'alert-success')
    return redirect(reverse('applications'))


def application_reject(request, app_id):
    application = get_object_or_404(Application, id=app_id)
    application.status = 'rejected'
    application.save()
    messages.warning(request, 'Заявка отклонена', 'alert-warning')
    return redirect(reverse('applications'))


def application_see(request, app_id):
    application = get_object_or_404(Application, id=app_id)
    context = get_base_context('Просмотр согласия', request)
    context['agreement'] = application.agreement
    return render(request, 'pages/moderation/application_see.html', context)


@login_required
def category_characteristics_page(request, category_id):
    category = get_object_or_404(ProductCategory, id=category_id)
    context = get_base_context('Управление характеристиками', request)
    context['category'] = category
    context['characteristics'] = category.categorycharacteristic_set.all()
    return render(request, 'pages/category/characteristics.html', context)


def category_characteristics_edit_form(request, category_id, char_id):
    get_object_or_404(ProductCategory, id=category_id)
    characteristic = get_object_or_404(CategoryCharacteristic, id=char_id)
    form = CategoryCharacteristicForm(category_id, char_id, instance=characteristic)
    if request.method == "POST":
        form = CategoryCharacteristicForm(category_id, char_id, request.POST,
                                          instance=characteristic)
        if form.is_valid():
            form.save()
        return redirect(reverse('category_characteristics', kwargs={'category_id': category_id}))
    return render(request, 'pages/category/characteristic_edit.html', {'form': form})


def goods_create_form(request, cat_id):
    category = get_object_or_404(ProductCategory, id=cat_id)
    product_form = ProductAddingForm(initial={'category': category})
    product_form.fields['category'].widget = forms.HiddenInput()
    characteristics = CategoryCharacteristic.objects.filter(category=category)
    data = [{'product': None,
             'characteristic': characteristic} for characteristic in characteristics]
    character_formset = formset_factory(ProductCharacteristicForm, extra=0)
    formset = character_formset(initial=data)

    for form in formset.forms:
        form.fields['value'].label = form.initial['characteristic'].name.capitalize()
        form.fields['characteristic'].widget = forms.HiddenInput()

    context = {
        'success': True,
        'error': None,
        'data': render_to_string(
            'base/product_add_form.html', {
                'product_form': product_form,
                'formset': formset
            }
        )
    }
    return JsonResponse(context)


@login_required
def review_add(request):
    context = get_base_context('Создание сравнительного обзора', request)

    if request.method == "GET":
        first_id = int(request.GET['first_id'])
        product = get_object_or_404(Product, id=first_id)
        form = ComparingReviewForm(
            initial={
                'author': request.user,
                'first': product
            }
        )
        context['form'] = form

    if request.method == "POST":
        form = ComparingReviewForm(request.POST)

        if form.is_valid():
            if form.cleaned_data['first'].category == form.cleaned_data['second'].category:
                review = form.save()
                messages.success(request, 'Сравнительный обзор успешно создан', 'alert-success')
                request.user.review_bonuses()
                return redirect(reverse('comparing_review', kwargs={'rev_id': review.id}))
            messages.error(request,
                           'Невозможно сравнить товары из разных категорий!',
                           'alert-danger')
            context['form'] = form

    return render(request, 'pages/comparing_review/review_add.html', context)


def review_selector_change(request):
    """ Function that return response with new second
    <select> to ajax-request from '/review_add/' """
    if not is_ajax(request):
        raise PermissionError('Only for JSON ajax-requests.')

    product_id = int(request.GET.get('product_id', None))
    product = get_object_or_404(Product, id=product_id)
    form = ComparingReviewForm(
        initial={
            'author': request.user,
            'first': product
        }
    )
    html = form.fields['second'].get_bound_field(form, 'second')
    context = {
        'success': True,
        'error': None,
        'data': str(html)
    }
    return JsonResponse(data=context)


def catalog_reviews(request):
    context = get_base_context('Каталог обзоров', request)
    context['categories'] = ProductCategory.objects.all()
    if 'category' in request.GET:
        # фильтруем по категории
        category_id = request.GET.get('category')
        try:
            category = get_object_or_404(ProductCategory, id=int(category_id))
            context['filter_category'] = category
            reviews = ComparingReview.objects.filter(first__category=category)
        except ValueError as value_error:
            raise Http404 from value_error
    elif 'product' in request.GET:
        product_id = request.GET.get('product')
        try:
            product = get_object_or_404(Product, id=int(product_id))
            reviews = product.get_reviews_with_product()
        except ValueError as value_error:
            raise Http404 from value_error
    else:
        reviews = ComparingReview.objects.all()
    context['reviews'] = reviews
    return render(request, 'pages/catalog/catalog_reviews.html', context)


def search_product(request):
    """
    Returns JSON response with search results

    This should then be implemented with ajax in the front-end so that
    as-you-type-search can be gracefully implemented
    All that needs to be done is this route has to be hit in order to get the search results
    And the html for it in a json response. The html for the results will
    be found by the key "html_from_view"
    """
    if not is_ajax(request):
        raise PermissionError('Only for JSON ajax-requests.')

    context = {}
    search_term = request.GET.get("input_value")

    products = Product.objects.filter(title__icontains=search_term)[:8]

    if len(products) == 0:
        products = Product.objects.all().order_by('rating')[:8]

    context["products"] = products

    html = render_to_string(template_name="base/products-search-list.html", context=context)
    data_dict = {"html_from_view": html}
    return JsonResponse(data=data_dict)
