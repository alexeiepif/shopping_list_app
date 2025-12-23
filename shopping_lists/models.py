from django.contrib.auth.models import User  # Django User model
from django.db import models


class ShoppingList(models.Model):
    name = models.CharField(max_length=255)
    # Владелец списка. Если пользователь удаляется, его списки также удаляются.
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="owned_lists"
    )
    # Пользователи, которым предоставлен доступ к этому списку (многие-ко-многим связь)
    shared_with = models.ManyToManyField(User, related_name="shared_lists", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ShoppingListItem(models.Model):
    # Связь с конкретным списком покупок. Если список удаляется, элементы тоже удаляются.
    shopping_list = models.ForeignKey(
        ShoppingList, on_delete=models.CASCADE, related_name="items"
    )
    name = models.CharField(max_length=255, blank=True)
    quantity = models.CharField(
        max_length=50, blank=True, null=True
    )  # Например: "2 шт", "1 кг"
    subcategory_notes = models.CharField(
        max_length=500, blank=True, null=True, verbose_name="Подкатегория/Примечания"
    )
    image = models.ImageField(
        upload_to="item_images/",
        blank=True,
        null=True,
        verbose_name="Изображение товара",
    )
    is_completed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.shopping_list.name})"

    class Meta:
        ordering = ["created_at"]  # Сортировка элементов по дате создания (новые снизу)
