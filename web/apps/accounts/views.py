__all__ = ()

import asyncio
import json
import secrets

from apps.accounts.forms import (
    AvatarUploadForm,
    CustomAuthenticationForm,
    CustomUserCreationForm,
    EmailChangeForm,
    PasswordChangeForm,
    ProfileEditForm,
)
from apps.accounts.models import ChatMessage, Notification
from apps.utils import (
    send_email_change_confirmation,
    send_password_changed_email,
    send_password_reset_email,
    send_verification_email,
)

from asgiref.sync import sync_to_async

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    login,
    logout,
    update_session_auth_hash,
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.contrib.auth.views import PasswordResetView
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

import requests

from social_django.models import UserSocialAuth


@sync_to_async
def get_user_async(request):
    user = request.user
    if user.is_authenticated:
        return user

    return None


class AnonymousRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return not self.request.user.is_authenticated

    def handle_no_permission(self):
        return redirect("accounts:profile")


class AuthView(AnonymousRequiredMixin, TemplateView):
    template_name = "accounts/auth.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["login_form"] = CustomAuthenticationForm()
        context["register_form"] = CustomUserCreationForm()
        return context

    def post(self, request, *args, **kwargs):
        if request.POST.get("action") == "login":
            form = CustomAuthenticationForm(request, data=request.POST)
            if form.is_valid():
                username = form.cleaned_data.get("username")
                password = form.cleaned_data.get("password")
                user = authenticate(username=username, password=password)

                if user is not None:
                    if not user.profile.email_verified:
                        messages.error(
                            request,
                            "Ваш email не подтвержден. "
                            "Проверьте почту или зарегистрируйтесь заново.",
                        )
                        return redirect("accounts:auth")

                    login(request, user)
                    Notification.objects.create(
                        profile=user.profile,
                        title="Вход в аккаунт",
                        description="Вы успешно вошли в систему.",
                    )
                    return redirect(
                        request.GET.get("next", "accounts:profile"),
                    )

            context = self.get_context_data()
            context["login_form"] = form
            context["active_tab"] = "login"
            return self.render_to_response(context)

        elif request.POST.get("action") == "register":
            form = CustomUserCreationForm(request.POST)
            if form.is_valid():
                user = form.save(commit=False)
                user.is_active = False
                user.save()

                token = secrets.token_urlsafe(32)
                profile = user.profile
                profile.email_verification_token = token
                profile.email_verification_token_created = timezone.now()
                profile.email_verified = False
                profile.save()

                verification_link = (
                    f"{request.scheme}://{request.get_host()}"
                    f"/auth/verify-email/{token}/"
                )
                send_verification_email(user, verification_link)

                messages.success(
                    request,
                    f"Письмо с подтверждением отправлено на {user.email}. Проверьте почту!",
                )
                return redirect("accounts:auth")

            context = self.get_context_data()
            context["register_form"] = form
            context["active_tab"] = "register"
            return self.render_to_response(context)

        return redirect("accounts:auth")


class VerifyEmailView(View):
    def get(self, request, token):
        from apps.accounts.models import Profile

        try:
            profile = Profile.objects.get(email_verification_token=token)
            user = profile.user

            if profile.email_verification_token_created:
                time_diff = (
                    timezone.now() - profile.email_verification_token_created
                )
                if time_diff.total_seconds() > 86400:  # 24 часа
                    messages.error(
                        request,
                        "Ссылка для подтверждения истекла. Зарегистрируйтесь заново.",
                    )
                    user.delete()
                    return redirect("accounts:auth")

            user.is_active = True
            user.save()
            profile.email_verified = True
            profile.email_verification_token = None
            profile.email_verification_token_created = None
            profile.save()

            messages.success(
                request,
                "Email успешно подтвержден! Теперь вы можете войти в аккаунт.",
            )
            return redirect("accounts:auth")

        except Profile.DoesNotExist:
            messages.error(request, "Неверная ссылка для подтверждения")
            return redirect("accounts:auth")


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"
    login_url = "accounts:auth"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["profile_form"] = ProfileEditForm(instance=self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        if "avatar" in request.FILES:
            form = AvatarUploadForm(request.POST, request.FILES)
            if form.is_valid():
                profile = request.user.profile
                if profile.avatar:
                    profile.avatar.delete()

                profile.avatar = form.cleaned_data["avatar"]
                profile.save()

            return redirect("accounts:profile")
        else:
            form = ProfileEditForm(request.POST, instance=request.user)
            if form.is_valid():
                form.save()
                return redirect("accounts:profile")

            context = self.get_context_data()
            context["profile_form"] = form
            return self.render_to_response(context)


class LogoutView(LoginRequiredMixin, View):
    login_url = "accounts:auth"

    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect("accounts:auth")


class NotificationsListAPIView(LoginRequiredMixin, View):
    login_url = "accounts:auth"

    def get(self, request, *args, **kwargs):
        profile = request.user.profile
        filter_type = request.GET.get("filter", "all")

        if filter_type == "unread":
            notifications = profile.notifications.filter(is_read=False)
        else:
            notifications = profile.notifications.all()

        data = []
        for n in notifications[:50]:
            data.append(
                {
                    "id": n.id,
                    "title": n.title,
                    "description": n.description,
                    "link": n.link,
                    "is_read": n.is_read,
                    "created_at": n.created_at.strftime("%H:%M"),
                },
            )

        return JsonResponse(
            {
                "notifications": data,
                "unread_count": profile.unread_notifications_count(),
            },
        )


class MarkAllReadView(LoginRequiredMixin, View):
    login_url = "accounts:auth"

    def post(self, request, *args, **kwargs):
        profile = request.user.profile
        profile.notifications.filter(is_read=False).update(is_read=True)
        return JsonResponse({"status": "ok"})


@method_decorator(csrf_exempt, name="dispatch")
class ChatAPIView(View):
    def _response_messages(self, messages, last_id):
        data = [
            {
                "id": m.id,
                "message": m.message,
                "is_admin": m.is_admin,
                "time": m.created_at.strftime("%H:%M"),
            }
            for m in messages
        ]
        new_last_id = messages[-1].id if messages else last_id
        return JsonResponse({"messages": data, "last_id": new_last_id})

    async def get(self, request, *args, **kwargs):
        user = await get_user_async(request)
        if not user.is_authenticated:
            return JsonResponse({"error": "Unauthorized"}, status=401)

        last_id = int(request.GET.get("last_id", 0))

        @sync_to_async
        def fetch_messages():
            return list(
                ChatMessage.objects.filter(
                    user_id=user.id,
                    id__gt=last_id,
                ).order_by("created_at"),
            )

        timeout = 30
        try:
            for _ in range(timeout):
                new_msgs = await fetch_messages()
                if new_msgs:
                    return self._response_messages(new_msgs, last_id)

                await asyncio.sleep(1)
        except (asyncio.CancelledError, RuntimeError, KeyboardInterrupt):
            return JsonResponse({"messages": [], "last_id": last_id})

        return JsonResponse(
            {
                "messages": [],
                "last_id": last_id,
                "timeout": True,
            },
        )

    async def post(self, request, *args, **kwargs):
        user = await get_user_async(request)
        if not user.is_authenticated:
            return JsonResponse({"error": "Unauthorized"}, status=401)

        body = json.loads(request.body)
        message = body.get("message", "")
        if message:
            msg = await ChatMessage.objects.acreate(
                user_id=user.id,
                message=message,
                is_admin=False,
            )
            return JsonResponse(
                {
                    "status": "ok",
                    "message": {
                        "id": msg.id,
                        "message": msg.message,
                        "is_admin": msg.is_admin,
                        "time": msg.created_at.strftime("%H:%M"),
                    },
                },
            )

        return JsonResponse({"status": "error"}, status=400)


class AdminChatListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "accounts/admin_chat.html"
    login_url = "accounts:auth"

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def handle_no_permission(self):
        return redirect("accounts:profile")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        users = User.objects.filter(chat_messages__isnull=False).distinct()
        user_data = []
        for user in users:
            last_msg = ChatMessage.objects.filter(user=user).last()
            user_data.append(
                {
                    "user": user,
                    "last_message": last_msg.message[:50] if last_msg else "",
                    "last_time": (
                        last_msg.created_at.strftime("%H:%M")
                        if last_msg
                        else ""
                    ),
                },
            )

        context["users_data"] = user_data
        return context


@method_decorator(csrf_exempt, name="dispatch")
class AdminChatMessagesAPIView(View):
    def _response_messages(self, messages, last_id):
        data = [
            {
                "id": m.id,
                "message": m.message,
                "is_admin": m.is_admin,
                "time": m.created_at.strftime("%H:%M"),
            }
            for m in messages
        ]
        new_last_id = messages[-1].id if messages else last_id
        return JsonResponse({"messages": data, "last_id": new_last_id})

    async def get(self, request, user_id, *args, **kwargs):
        user = await get_user_async(request)
        if not user.is_authenticated or not (
            user.is_staff or user.is_superuser
        ):
            return JsonResponse({"error": "Forbidden"}, status=403)

        last_id = int(request.GET.get("last_id", 0))

        @sync_to_async
        def fetch_messages():
            return list(
                ChatMessage.objects.filter(
                    user_id=user_id,
                    id__gt=last_id,
                ).order_by("created_at"),
            )

        timeout = 30
        try:
            for _ in range(timeout):
                new_msgs = await fetch_messages()
                if new_msgs:
                    return self._response_messages(new_msgs, last_id)

                await asyncio.sleep(1)
        except (asyncio.CancelledError, RuntimeError, KeyboardInterrupt):
            return JsonResponse({"messages": [], "last_id": last_id})

        return JsonResponse(
            {
                "messages": [],
                "last_id": last_id,
                "timeout": True,
            },
        )

    async def post(self, request, user_id, *args, **kwargs):
        user = await get_user_async(request)
        if not user.is_authenticated or not (
            user.is_staff or user.is_superuser
        ):
            return JsonResponse({"error": "Forbidden"}, status=403)

        body = json.loads(request.body)
        message = body.get("message", "")
        if message:
            msg = await ChatMessage.objects.acreate(
                user_id=user_id,
                message=message,
                is_admin=True,
            )
            return JsonResponse(
                {
                    "status": "ok",
                    "message": {
                        "id": msg.id,
                        "message": msg.message,
                        "is_admin": msg.is_admin,
                        "time": msg.created_at.strftime("%H:%M"),
                    },
                },
            )

        return JsonResponse({"status": "error"}, status=400)


class DisconnectAccountView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/disconnect_account.html"
    login_url = "accounts:auth"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        provider = self.kwargs.get("provider")
        context["provider"] = provider

        provider_names = {
            "yandex-oauth2": "Яндекс",
            "github": "GitHub",
            "google-oauth2": "Google",
        }
        context["provider_name"] = provider_names.get(provider, provider)

        has_provider = UserSocialAuth.objects.filter(
            user=self.request.user,
            provider=provider,
        ).exists()
        context["has_provider"] = has_provider
        return context

    def dispatch(self, request, *args, **kwargs):
        provider = kwargs.get("provider")
        has_provider = UserSocialAuth.objects.filter(
            user=request.user,
            provider=provider,
        ).exists()
        if not has_provider:
            provider_names = {
                "yandex-oauth2": "Яндекс",
                "github": "GitHub",
                "google-oauth2": "Google",
            }
            messages.warning(
                request,
                f"Ваш аккаунт не связан с {provider_names.get(provider, provider)}",
            )
            return redirect("accounts:profile")

        return super().dispatch(request, *args, **kwargs)


class DisconnectConfirmView(LoginRequiredMixin, View):
    login_url = "accounts:auth"

    def post(self, request, *args, **kwargs):
        provider = kwargs.get("provider")

        if not provider:
            messages.error(request, "Провайдер не указан")
            return redirect("accounts:profile")

        try:
            social_auth = UserSocialAuth.objects.get(
                user=request.user,
                provider=provider,
            )

            if provider == "yandex-oauth2":
                access_token = social_auth.extra_data.get("access_token")
                if access_token:
                    try:
                        revoke_url = "https://oauth.yandex.ru/revoke_token"
                        requests.post(
                            revoke_url,
                            data={"token": access_token},
                            timeout=10,
                        )
                    except Exception:
                        pass

            social_auth.delete()

            provider_names = {
                "yandex-oauth2": "Яндекс",
                "github": "GitHub",
                "google-oauth2": "Google",
            }
            provider_name = provider_names.get(provider, provider)

            if not request.user.has_usable_password():
                messages.warning(
                    request,
                    f"Вы отключили вход через {provider_name}. "
                    f"Установите пароль для входа в аккаунт.",
                )
                update_session_auth_hash(request, request.user)
                return redirect("accounts:set_password")

            messages.success(
                request,
                f"Вы успешно отключили аккаунт от {provider_name}",
            )
            return redirect("accounts:profile")

        except UserSocialAuth.DoesNotExist:
            messages.error(request, "Аккаунт не связан с этим провайдером")
            return redirect("accounts:profile")
        except Exception as e:
            messages.error(request, f"Ошибка при отключении: {str(e)}")
            return redirect("accounts:profile")


class SetPasswordView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/set_password.html"
    login_url = "accounts:auth"

    def dispatch(self, request, *args, **kwargs):
        if request.user.has_usable_password():
            return redirect("accounts:profile")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "password1" in kwargs:
            context["password1"] = kwargs.get("password1", "")
            context["password2"] = kwargs.get("password2", "")

        return context

    def post(self, request, *args, **kwargs):
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        errors = []

        if not password1 or not password2:
            errors.append("Заполните оба поля")
        elif password1 != password2:
            errors.append("Пароли не совпадают")
        elif len(password1) < 8:
            errors.append("Пароль должен быть не менее 8 символов")
        else:
            request.user.set_password(password1)
            request.user.save()

            update_session_auth_hash(request, request.user)

            return redirect("accounts:profile")

        context = self.get_context_data(
            password1=password1,
            password2=password2,
            errors=errors,
        )
        return self.render_to_response(context)


class CustomPasswordResetView(PasswordResetView):
    template_name = "accounts/password_reset.html"
    email_template_name = "email/password_reset.html"
    subject_template_name = "email/password_reset_subject.txt"
    success_url = "/auth/password-reset/done/"
    from_email = settings.DEFAULT_FROM_EMAIL

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        from django.contrib.auth.models import User
        from django.contrib.sites.shortcuts import get_current_site
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.contrib.auth.tokens import default_token_generator

        user = User.objects.filter(email=email).first()

        if not user:
            form.add_error(
                "email",
                "Пользователь с таким e-mail не зарегистрирован.",
            )
            return self.form_invalid(form)

        current_site = get_current_site(self.request)
        reset_link = (
            f"{self.request.scheme}://{current_site.domain}"
            f"/auth/password-reset/{urlsafe_base64_encode(force_bytes(user.pk))}"
            f"/{default_token_generator.make_token(user)}/"
        )
        send_password_reset_email(user, reset_link)

        return super().form_valid(form)


class PasswordChangeView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/password_change.html"
    login_url = "accounts:auth"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "form" not in kwargs:
            context["form"] = PasswordChangeForm(user=self.request.user)

        return context

    def post(self, request, *args, **kwargs):
        form = PasswordChangeForm(user=request.user, data=request.POST)

        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)

            if request.user.email:
                try:
                    send_password_changed_email(request.user)
                except Exception:
                    pass

            return redirect("accounts:profile")

        context = self.get_context_data(form=form)
        return self.render_to_response(context)


class ChangeEmailView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/change_email.html"
    login_url = "accounts:auth"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "form" not in kwargs:
            context["form"] = EmailChangeForm(user=self.request.user)

        return context

    def post(self, request, *args, **kwargs):
        form = EmailChangeForm(user=request.user, data=request.POST)

        if form.is_valid():
            new_email = form.cleaned_data["new_email"]
            profile = request.user.profile

            token = secrets.token_urlsafe(32)
            profile.new_email = new_email
            profile.new_email_token = token
            profile.new_email_token_created = timezone.now()
            profile.save()

            confirmation_link = (
                f"{request.scheme}://{request.get_host()}"
                f"/auth/confirm-email-change/{token}/"
            )
            send_email_change_confirmation(
                request.user,
                new_email,
                confirmation_link,
            )

            messages.success(
                request,
                f"Письмо с подтверждением отправлено на {new_email}. Проверьте почту!",
            )
            return redirect("accounts:profile")

        context = self.get_context_data(form=form)
        return self.render_to_response(context)


class ConfirmEmailChangeView(View):
    def get(self, request, token):
        from apps.accounts.models import Profile

        try:
            profile = Profile.objects.get(new_email_token=token)
            user = profile.user

            if profile.new_email_token_created:
                time_diff = timezone.now() - profile.new_email_token_created
                if time_diff.total_seconds() > 86400:
                    messages.error(
                        request,
                        "Ссылка для подтверждения истекла. Попробуйте снова.",
                    )
                    return redirect("accounts:profile")

            user.email = profile.new_email
            user.save()

            profile.new_email = None
            profile.new_email_token = None
            profile.new_email_token_created = None
            profile.email_verified = True
            profile.save()

            messages.success(
                request,
                f"Email успешно изменен на {user.email}!",
            )
            return redirect("accounts:profile")

        except Profile.DoesNotExist:
            messages.error(request, "Неверная ссылка для подтверждения")
            return redirect("accounts:profile")
