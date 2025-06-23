# shopping_lists/serializers.py
from django.contrib.auth.models import User
from rest_framework import serializers

from .models import ShoppingList, ShoppingListItem


# Сериализатор для пользователя (для отображения информации о владельце и тех, с кем поделено)
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
        ]  # Какие поля пользователя мы хотим раскрывать в API


# Сериализатор для элементов списка покупок
class ShoppingListItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingListItem
        fields = [
            "id",
            "name",
            "quantity",
            "subcategory_notes",
            "image",
            "is_completed",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]  # Поля, которые не могут быть изменены клиентом


# Сериализатор для списков покупок
class ShoppingListSerializer(serializers.ModelSerializer):
    # Вложенный сериализатор для отображения элементов списка вместе со списком
    items = ShoppingListItemSerializer(many=True, read_only=True)
    # Вложенный сериализатор для отображения владельца списка
    owner = UserSerializer(read_only=True)
    # Вложенный сериализатор для отображения пользователей, с которыми поделен список
    shared_with = UserSerializer(many=True, read_only=True)
    # Поле для удобства добавления пользователей в shared_with по их username или email
    # Это поле не из модели, оно только для записи (write_only) при создании/обновлении
    # Позволяет отправлять список имен пользователей или ID для "поделиться"
    shared_with_usernames = serializers.ListField(
        child=serializers.CharField(max_length=150), write_only=True, required=False
    )

    class Meta:
        model = ShoppingList
        fields = [
            "id",
            "name",
            "owner",
            "items",
            "shared_with",
            "created_at",
            "updated_at",
            "shared_with_usernames",
        ]
        read_only_fields = [
            "id",
            "owner",
            "items",
            "shared_with",
            "created_at",
            "updated_at",
        ]  # Поля, которые не могут быть изменены клиентом (owner и shared_with изменяются через отдельную логику)

    def create(self, validated_data):
        # При создании списка, владелец устанавливается из текущего запроса
        # shared_with_usernames обрабатывается отдельно, если есть
        shared_with_usernames = validated_data.pop("shared_with_usernames", [])
        shopping_list = ShoppingList.objects.create(**validated_data)
        if shared_with_usernames:
            users_to_share = User.objects.filter(username__in=shared_with_usernames)
            shopping_list.shared_with.set(users_to_share)
        return shopping_list

    def update(self, instance, validated_data):
        # При обновлении списка, обновляем имя
        instance.name = validated_data.get("name", instance.name)

        # Обрабатываем shared_with_usernames при обновлении
        shared_with_usernames = validated_data.pop("shared_with_usernames", None)
        if shared_with_usernames is not None:
            users_to_share = User.objects.filter(username__in=shared_with_usernames)
            instance.shared_with.set(
                users_to_share
            )  # Перезаписываем всех, с кем поделено

        instance.save()
        return instance
