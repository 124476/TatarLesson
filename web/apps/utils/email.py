__all__ = ()

from django.conf import settings
from django.template.loader import render_to_string

import requests


def send_html_email(
    to_email,
    subject,
    template_name,
    context,
    from_email=None,
):
    if not to_email:
        return False

    if isinstance(to_email, str):
        to_email = [to_email]

    try:
        html_message = render_to_string(template_name, context)
        text_message = render_to_string(
            template_name.replace(".html", ".txt"),
            context,
        )
    except Exception:
        text_message = html_message

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": from_email or settings.DEFAULT_FROM_EMAIL,
                "to": to_email,
                "subject": subject,
                "html": html_message,
                "text": text_message,
            },
        )

        if response.status_code == 200:
            return True
        else:
            return False
    except Exception:
        return False


def send_password_reset_email(user, reset_link):
    return send_html_email(
        to_email=user.email,
        subject="Восстановление пароля",
        template_name="email/password_reset.html",
        context={
            "user": user,
            "reset_link": reset_link,
        },
    )


def send_password_changed_email(user):
    return send_html_email(
        to_email=user.email,
        subject="Пароль изменен",
        template_name="email/password_changed.html",
        context={
            "user": user,
        },
    )


def send_verification_email(user, verification_link):
    return send_html_email(
        to_email=user.email,
        subject="Подтверждение email",
        template_name="email/verification.html",
        context={
            "user": user,
            "verification_link": verification_link,
        },
    )


def send_email_change_confirmation(user, new_email, confirmation_link):
    return send_html_email(
        to_email=new_email,
        subject="Подтверждение смены email",
        template_name="email/email_change_confirmation.html",
        context={
            "user": user,
            "new_email": new_email,
            "confirmation_link": confirmation_link,
        },
    )
