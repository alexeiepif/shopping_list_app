# shopping_lists/urls.py
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from .views import ShoppingListItemViewSet, ShoppingListViewSet

router = DefaultRouter()
router.register(r"lists", ShoppingListViewSet, basename="list")  # /api/v1/lists/

# Вложенный роутер для элементов списка
# Элементы списка будут доступны по URL вида /api/v1/lists/{list_id}/items/
lists_router = routers.NestedSimpleRouter(router, r"lists", lookup="shopping_list")
lists_router.register(r"items", ShoppingListItemViewSet, basename="list-items")

urlpatterns = [
    path("", include(router.urls)),
    path("", include(lists_router.urls)),
]
