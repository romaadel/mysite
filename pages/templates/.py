# context_processors.py
from .models import Product

def category_list(request):
    categories = Product.objects.values_list('category', flat=True).distinct()
    selected_category = request.GET.get('category')
    return {
        'categories': categories,
        'selected_category': selected_category
    }
