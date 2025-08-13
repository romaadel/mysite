from collections import defaultdict
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage

from django import forms
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse

from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import translation
from django.views.decorators.http import require_POST
from django.http import HttpResponse

from .forms import CheckoutForm, RegisterForm
from .models import Product, Review, Order, OrderItem
from django.shortcuts import redirect


# -------------------- تغيير اللغة --------------------
def set_language(request):
    lang_code = request.GET.get('lang', 'en')
    if lang_code in ['en', 'ar']:
        request.session['django_language'] = lang_code

    return redirect(request.META.get('HTTP_REFERER', '/'))


# -------------------- النماذج --------------------
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'category', 'price', 'rating', 'image']


# -------------------- عرض المنتجات --------------------
def products(request):
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()

    products_qs = Product.objects.all()

    if category and category != "All":
        products_qs = products_qs.filter(category__iexact=category)

    if query:
        products_qs = products_qs.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    categories = list(Product.objects.values_list("category", flat=True).distinct())
    categories.insert(0, "All")
    worthy_products = Product.objects.filter(is_worthy_pick=True)

    return render(request, 'pages/products.html', {
        'products': products_qs,
        'worthy_products': worthy_products,
        'selected_category': category,
        'categories': categories,
        'search_query': query,
    })


# -------------------- تفاصيل المنتج والتقييم --------------------
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    reviews = product.reviews.select_related('user').all()

    # If the user is logged in and submitting a review form
    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.error(request, "You must be logged in to add a review.")
            return redirect('login')

        rating = request.POST.get("rating")
        comment = request.POST.get("comment", "").strip()

        try:
            rating_int = int(rating)
            if not (1 <= rating_int <= 5):
                raise ValueError
        except (TypeError, ValueError):
            messages.error(request, "Invalid rating.")
            return redirect('product_detail', product_id=product_id)

        if not comment:
            messages.error(request, "Please write a comment.")
            return redirect('product_detail', product_id=product_id)

        if Review.objects.filter(product=product, user=request.user).exists():
            messages.error(request, "You have already reviewed this product.")
        else:
            Review.objects.create(
                product=product,
                user=request.user,
                rating=rating_int,
                comment=comment
            )
            messages.success(request, "Your review has been added successfully.")
            return redirect('product_detail', product_id=product_id)

    return render(request, 'pages/product_detail.html', {
        'product': product,
        'reviews': reviews
    })



def sale_page(request):
    products = Product.objects.filter(on_sale=True)
    return render(request, 'pages/sale.html', {'products': products})


@login_required
def manage_products(request):
    products_qs = Product.objects.filter(owner=request.user)
    return render(request, 'pages/manage_products.html', {'products': products_qs})


@login_required
def profile_view(request):
    user_products = Product.objects.filter(owner=request.user)
    return render(request, 'pages/profile.html', {
        'user_products': user_products,
        'username': request.user.username
    })


# -------------------- CRUD المنتجات --------------------
@login_required
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.owner = request.user
            product.save()
            return redirect('manage_products')
    else:
        form = ProductForm()

    return render(request, 'pages/add_product.html', {'form': form})


@login_required
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.user != product.owner:
        return HttpResponse("❌ لا تملك صلاحية التعديل.", status=403)

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect('manage_products')
    else:
        form = ProductForm(instance=product)

    return render(request, 'pages/edit_product.html', {'form': form})


@login_required
@require_POST
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.user != product.owner:
        return HttpResponse("❌ لا تملك صلاحية الحذف.", status=403)
    product.delete()
    return redirect('manage_products')


# -------------------- تسجيل الدخول/الخروج --------------------
from django.urls import reverse
def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()


            current_site = get_current_site(request)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            activate_url = reverse('activate', kwargs={'uidb64': uid, 'token': token})
            activate_url = f"http://{current_site.domain}{activate_url}"


            message = render_to_string('pages/activation_email.html', {
                'user': user,
                'activation_link': activate_url,
            })

            email = EmailMessage(
                'Activate Your Account',
                message,
                to=[user.email]
            )
            email.content_subtype = "html"
            email.send()


            return render(request, 'pages/verify_email_page.html', {'activation_link': activate_url})

    else:
        form = RegisterForm()
    return render(request, 'pages/register.html', {'form': form})



def activate(request, uidb64, token):
    User = get_user_model()
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, "Your account has been activated successfully!")
        return redirect('login')
    else:
        messages.error(request, "Activation link is invalid!")
        return redirect('register')



def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('products')
    else:
        form = AuthenticationForm()
    return render(request, 'pages/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


# -------------------- السلة --------------------
def get_cart_items(request):
    cart = request.session.get('cart', {})
    items = []
    total = Decimal('0.00')

    if not cart:
        return items, total

    product_ids = [int(pid) for pid in cart.keys()]
    products = Product.objects.filter(id__in=product_ids)
    prod_map = {p.id: p for p in products}

    for pid_str, qty in cart.items():
        pid = int(pid_str)
        product = prod_map.get(pid)
        if not product:
            continue
        qty_int = int(qty)
        subtotal = (product.price * qty_int)
        items.append({'product': product, 'quantity': qty_int, 'subtotal': subtotal})
        total += subtotal

    return items, total


@login_required
def cart_view(request):
    items, total = get_cart_items(request)
    return render(request, 'pages/cart.html', {'items': items, 'total': total})


@login_required
@require_POST
def add_to_cart(request, product_id):
    cart = request.session.get('cart', {})
    cart[str(product_id)] = cart.get(str(product_id), 0) + 1
    request.session['cart'] = cart
    return redirect('products')


@login_required
@require_POST
def remove_from_cart(request, product_id):
    cart = request.session.get('cart', {})
    pid = str(product_id)
    if pid in cart:
        cart.pop(pid)
        request.session['cart'] = cart
    return redirect('cart')


@login_required
@require_POST
def update_cart(request, product_id):
    cart = request.session.get('cart', {})
    pid = str(product_id)
    qty = request.POST.get('quantity', '1')
    try:
        qty_int = max(0, int(qty))
    except ValueError:
        qty_int = 1
    if qty_int <= 0:
        cart.pop(pid, None)
    else:
        cart[pid] = qty_int
    request.session['cart'] = cart
    return redirect('cart')


# -------------------- الدفع والطلبات --------------------
@login_required
def checkout(request):
    items, total = get_cart_items(request)
    if not items:
        messages.error(request, "سلة التسوق فارغة.")
        return redirect('products')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            order = Order.objects.create(
                user=request.user,
                full_name=cd['full_name'],
                address=cd['address'],
                phone=cd.get('phone', ''),
                note=cd.get('note', ''),
                total=total
            )
            for it in items:
                OrderItem.objects.create(
                    order=order,
                    product=it['product'],
                    quantity=it['quantity'],
                    price=it['product'].price
                )
            request.session['cart'] = {}
            messages.success(request, f"تم إنشاء الطلب بنجاح. رقم الطلب #{order.id}")
            return redirect('order_detail', order_id=order.id)
    else:
        form = CheckoutForm(initial={'full_name': request.user.get_full_name() or request.user.username})

    return render(request, 'pages/checkout.html', {'form': form, 'items': items, 'total': total})


@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'pages/my_orders.html', {'orders': orders})


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'pages/order_detail.html', {'order': order})


# -------------------- تواصل وصفحة رئيسية --------------------
def contact(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        message = request.POST.get("message")
        return render(request, "pages/contact.html", {"message_sent": True, "name": name})
    return render(request, "pages/contact.html")


def home(request):
    return render(request, 'pages/home.html')
