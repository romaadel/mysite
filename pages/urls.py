from django.urls import path, include
from . import views
from django.contrib.auth import views as auth_views
from .views import set_language
from django.shortcuts import redirect

def redirect_to_signup(request):
    return redirect('account_signup')

urlpatterns = [
    path('', views.home, name='home'),
    path('products/', views.products, name='products'),  
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('products/add/', views.add_product, name='add_product'),
    path('products/edit/<int:product_id>/', views.edit_product, name='edit_product'),
    path('products/delete/<int:product_id>/', views.delete_product, name='delete_product'),

    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:product_id>/', views.update_cart, name='update_cart'),

    path('checkout/', views.checkout, name='checkout'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),

    path('login/', auth_views.LoginView.as_view(template_name='pages/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),


    path('register/', views.register, name='register'),


    path('accounts/', include('allauth.urls')),

    path('manage-products/', views.manage_products, name='manage_products'),
    path('profile/', views.profile_view, name='profile'),
    path('set_language/', set_language, name='set_language'),
    path('sale/', views.sale_page, name='sale'),

  



    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
]
