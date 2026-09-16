__all__ = ()

from apps.news.models import News

from django.views.generic import DetailView, ListView


class NewsListView(ListView):
    model = News
    template_name = "news/list.html"
    context_object_name = "news_list"
    paginate_by = 6


class NewsDetailView(DetailView):
    model = News
    template_name = "news/detail.html"
    context_object_name = "news"
