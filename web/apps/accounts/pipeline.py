__all__ = ()

from django.contrib.auth.models import User

from social_core.exceptions import AuthAlreadyAssociated

from social_django.models import UserSocialAuth


def check_social_user(backend, uid, user=None, *args, **kwargs):
    if backend.name in ["yandex-oauth2", "github"]:
        social = UserSocialAuth.objects.filter(
            provider=backend.name,
            uid=uid,
        ).first()

        if social:
            if user and user.is_authenticated and social.user.id != user.id:
                raise AuthAlreadyAssociated(backend)

            if not user or not user.is_authenticated:
                return {"user": social.user}

        return


def associate_by_email(backend, details, user=None, *args, **kwargs):
    if backend.name in ["yandex-oauth2", "github", "google-oauth2"]:
        email = details.get("email")

        if not email:
            return

        if user and user.pk:
            existing_user = (
                User.objects.filter(email=email).exclude(id=user.id).first()
            )
            if existing_user:
                social = UserSocialAuth.objects.filter(
                    user=existing_user,
                    provider=backend.name,
                ).first()

                if social:
                    from django.contrib import messages

                    request = kwargs.get("request")
                    if request:
                        messages.error(
                            request,
                            "Этот аккаунт уже привязан к другому пользователю.",
                        )

                    return
                else:
                    return {
                        "user": existing_user,
                    }

            return

        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            return {"user": existing_user}


def save_avatar(backend, user, response, *args, **kwargs):
    avatar_url = None

    if backend.name == "yandex-oauth2":
        avatar_id = response.get("default_avatar_id")
        if avatar_id:
            avatar_url = (
                f"https://avatars.yandex.net/get-yapic/{avatar_id}/islands-200"
            )

    elif backend.name == "github":
        avatar_url = response.get("avatar_url")

    elif backend.name == "google-oauth2":
        avatar_url = response.get("picture")

    if avatar_url:
        if not user.profile.avatar and not user.profile.avatar_url:
            user.profile.avatar_url = avatar_url
            user.profile.save()


def verify_social_email(backend, user, *args, **kwargs):
    if user and hasattr(user, "profile"):
        if not user.profile.email_verified:
            user.profile.email_verified = True
            user.profile.save()
