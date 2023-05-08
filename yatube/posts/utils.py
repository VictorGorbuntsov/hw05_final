from django.core.paginator import Paginator
from django.conf import settings


def get_page_context(request, post_list):
    paginator = Paginator(post_list, settings.POSTS_ON_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj
