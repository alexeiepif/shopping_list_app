# shopping_lists/views.py
from django.contrib.auth.models import User
from django.db.models import (
    Q,
)  # Для сложных запросов (например, фильтрация по нескольким полям)
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import ShoppingList, ShoppingListItem
from .serializers import (
    ShoppingListItemSerializer,
    ShoppingListSerializer,
)


class ShoppingListViewSet(viewsets.ModelViewSet):
    serializer_class = ShoppingListSerializer
    permission_classes = [
        permissions.IsAuthenticated
    ]  # Только для аутентифицированных пользователей

    def get_queryset(self):
        # Пользователь может видеть:
        # 1. Свои собственные списки (owner=request.user)
        # 2. Списки, которые были ему предоставлены (shared_with=request.user)
        user = self.request.user
        return ShoppingList.objects.filter(
            Q(owner=user) | Q(shared_with=user)
        ).distinct()

    def perform_create(self, serializer):
        # При создании списка, устанавливаем текущего пользователя как владельца
        serializer.save(owner=self.request.user)

    @action(
        detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated]
    )
    def share(self, request, pk=None):
        """
        Поделиться списком с другим пользователем по имени пользователя или email.
        Принимает: {'username_or_email': 'another_user'}
        """
        shopping_list = self.get_object()
        # Проверяем, что текущий пользователь является владельцем списка
        if shopping_list.owner != request.user:
            return Response(
                {"detail": "У вас нет прав для изменения доступа к этому списку."},
                status=status.HTTP_403_FORBIDDEN,
            )

        username_or_email = request.data.get("username_or_email")
        if not username_or_email:
            return Response(
                {
                    "detail": "Требуется имя пользователя или email для предоставления доступа."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Пытаемся найти пользователя по username или email
            user_to_share_with = User.objects.get(
                Q(username=username_or_email) | Q(email=username_or_email)
            )
        except User.DoesNotExist:
            return Response(
                {"detail": "Пользователь с таким именем или email не найден."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if user_to_share_with == request.user:
            return Response(
                {"detail": "Нельзя поделиться списком с самим собой."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user_to_share_with in shopping_list.shared_with.all():
            return Response(
                {"detail": "Список уже предоставлен этому пользователю."},
                status=status.HTTP_409_CONFLICT,
            )

        shopping_list.shared_with.add(user_to_share_with)
        shopping_list.save(update_fields=["updated_at"])
        return Response(
            {
                "detail": f"Список успешно предоставлен пользователю {user_to_share_with.username}."
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated]
    )
    def unshare(self, request, pk=None):
        """
        Отменить доступ к списку для другого пользователя по имени пользователя или email.
        Принимает: {'username_or_email': 'another_user'}
        """
        shopping_list = self.get_object()
        # Проверяем, что текущий пользователь является владельцем списка
        if shopping_list.owner != request.user:
            return Response(
                {"detail": "У вас нет прав для изменения доступа к этому списку."},
                status=status.HTTP_403_FORBIDDEN,
            )

        username_or_email = request.data.get("username_or_email")
        if not username_or_email:
            return Response(
                {"detail": "Требуется имя пользователя или email для отзыва доступа."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user_to_unshare = User.objects.get(
                Q(username=username_or_email) | Q(email=username_or_email)
            )
        except User.DoesNotExist:
            return Response(
                {"detail": "Пользователь с таким именем или email не найден."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if user_to_unshare not in shopping_list.shared_with.all():
            return Response(
                {"detail": "У этого пользователя нет доступа к списку."},
                status=status.HTTP_409_CONFLICT,
            )

        shopping_list.shared_with.remove(user_to_unshare)
        shopping_list.save(update_fields=["updated_at"])
        return Response(
            {
                "detail": f"Доступ к списку отозван у пользователя {user_to_unshare.username}."
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated]
    )
    def leave(self, request, pk=None):
        """
        Пользователь, которому предоставили доступ, покидает список.
        """
        shopping_list = self.get_object()
        current_user = request.user

        # Владелец не может "покинуть" свой список, он может его только удалить или unshare
        if shopping_list.owner == current_user:
            return Response(
                {
                    "detail": "Вы являетесь владельцем этого списка и не можете его покинуть. Вы можете его удалить."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Проверяем, что пользователь действительно имеет доступ к этому списку через shared_with
        if current_user not in shopping_list.shared_with.all():
            return Response(
                {"detail": "У вас нет доступа к этому списку, чтобы его покинуть."},
                status=status.HTTP_403_FORBIDDEN,
            )

        shopping_list.shared_with.remove(current_user)
        shopping_list.save(update_fields=["updated_at"])
        return Response(
            {"detail": f'Вы успешно покинули список "{shopping_list.name}".'},
            status=status.HTTP_200_OK,
        )


class ShoppingListItemViewSet(viewsets.ModelViewSet):
    serializer_class = ShoppingListItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Пользователь может видеть элементы только тех списков, к которым у него есть доступ
        user = self.request.user
        # Получаем ID списка из URL (например, /api/v1/lists/1/items/)
        shopping_list_id = self.kwargs["shopping_list_pk"]
        # Фильтруем элементы по ID списка и по тому, что пользователь имеет к нему доступ
        return ShoppingListItem.objects.filter(
            Q(shopping_list__id=shopping_list_id)
            & (Q(shopping_list__owner=user) | Q(shopping_list__shared_with=user))
        ).distinct()

    def perform_create(self, serializer):
        # При создании элемента, связываем его с конкретным списком
        # Получаем ID списка из URL
        shopping_list_id = self.kwargs["shopping_list_pk"]
        shopping_list = ShoppingList.objects.get(id=shopping_list_id)

        # Проверка прав: только владелец или тот, с кем поделено, может добавлять элементы
        if (
            shopping_list.owner != self.request.user
            and self.request.user not in shopping_list.shared_with.all()
        ):
            raise permissions.PermissionDenied(
                "У вас нет прав добавлять элементы в этот список."
            )

        serializer.save(shopping_list=shopping_list)
        shopping_list.save(update_fields=["updated_at"])

    # Переопределяем perform_update, чтобы только владелец или тот, с кем поделено, мог изменять
    def perform_update(self, serializer):
        shopping_list = serializer.instance.shopping_list
        if (
            shopping_list.owner != self.request.user
            and self.request.user not in shopping_list.shared_with.all()
        ):
            raise permissions.PermissionDenied("У вас нет прав изменять этот элемент.")
        serializer.save()
        shopping_list.save(update_fields=["updated_at"])

    # Переопределяем perform_destroy, чтобы только владелец или тот, с кем поделено, мог удалять
    def perform_destroy(self, instance):
        shopping_list = instance.shopping_list
        if (
            shopping_list.owner != self.request.user
            and self.request.user not in shopping_list.shared_with.all()
        ):
            raise permissions.PermissionDenied("У вас нет прав удалять этот элемент.")
        instance.delete()
        shopping_list.save(update_fields=["updated_at"])
