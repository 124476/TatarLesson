__all__ = ()

import os
from pathlib import Path

import dj_database_url

from dotenv import load_dotenv

load_dotenv()


def load_bool(name, default):
    env_value = os.getenv(name, default=str(default)).lower()
    return env_value in ("true", "yes", "1", "y", "t", "on")


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", default="no_key")

DEBUG = load_bool("DJANGO_DEBUG", True)

ON_RENDER = load_bool("ON_RENDER", False)

ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", default="*").split(",")

INSTALLED_APPS = [
    "daphne",
    "apps.news.apps.NewsConfig",
    "apps.core.apps.CoreConfig",
    "apps.about.apps.AboutConfig",
    "apps.accounts.apps.AccountsConfig",
    "apps.homepage.apps.HomepageConfig",
    "apps.competitions.apps.CompetitionsConfig",
    "apps.dashboard.apps.DashboardConfig",
    "apps.lessons.apps.LessonsConfig",
    "apps.words.apps.WordsConfig",
    "apps.gamification.apps.GamificationConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "whitenoise.runserver_nostatic",
    "social_django",
    "storages",
    "ckeditor",
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.import_export",
    "unfold.contrib.guardian",
    "unfold.contrib.simple_history",
    "django.contrib.admin",
]

UNFOLD = {
    "SITE_TITLE": "Мой проект",
    "SITE_HEADER": "Админ панель",
    "SITE_URL": "/",
    "SITE_ICON": None,
    "DASHBOARD_CALLBACK": "apps.core.views.dashboard_callback",
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
    },
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "social_django.middleware.SocialAuthExceptionMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
]

AUTHENTICATION_BACKENDS = [
    "social_core.backends.google.GoogleOAuth2",
    "social_core.backends.github.GithubOAuth2",
    "social_core.backends.yandex.YandexOAuth2",
    "django.contrib.auth.backends.ModelBackend",
]

SOCIAL_AUTH_YANDEX_OAUTH2_KEY = os.getenv(
    "YANDEX_OAUTH2_KEY",
    default="no_key",
)
SOCIAL_AUTH_YANDEX_OAUTH2_SECRET = os.getenv(
    "YANDEX_OAUTH2_SECRET",
    default="no_key",
)
SOCIAL_AUTH_YANDEX_OAUTH2_SCOPE = ["login:info", "login:email", "login:avatar"]

SOCIAL_AUTH_GITHUB_KEY = os.getenv(
    "GITHUB_OAUTH2_KEY",
    default="no_key",
)
SOCIAL_AUTH_GITHUB_SECRET = os.getenv(
    "GITHUB_OAUTH2_SECRET",
    default="no_key",
)
SOCIAL_AUTH_GITHUB_SCOPE = ["user:email", "user:info", "user:avatar"]

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.getenv(
    "GOOGLE_OAUTH2_KEY",
    default="no_key",
)
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.getenv(
    "GOOGLE_OAUTH2_SECRET",
    default="no_key",
)
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = ["email", "profile"]

LOGIN_URL = "accounts:auth"
LOGIN_REDIRECT_URL = "accounts:profile"
LOGOUT_REDIRECT_URL = "accounts:auth"

SOCIAL_AUTH_USERNAME_IS_FULL_EMAIL = True

SOCIAL_AUTH_RAISE_EXCEPTIONS = False
SOCIAL_AUTH_HANDLE_EXCEPTIONS = True

SOCIAL_AUTH_PIPELINE = (
    "social_core.pipeline.social_auth.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.auth_allowed",
    "apps.accounts.pipeline.check_social_user",
    "social_core.pipeline.social_auth.social_user",
    "social_core.pipeline.user.get_username",
    "social_core.pipeline.user.create_user",
    "apps.accounts.pipeline.associate_by_email",
    "apps.accounts.pipeline.save_avatar",
    "apps.accounts.pipeline.verify_social_email",
    "social_core.pipeline.social_auth.associate_user",
    "social_core.pipeline.social_auth.load_extra_data",
    "social_core.pipeline.user.user_details",
)

ROOT_URLCONF = "web.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "web.wsgi.application"
ASGI_APPLICATION = "web.asgi.application"

DB_MODE = os.getenv("DB_MODE", default="sqlite").lower()
DATABASE_URL = os.getenv("DATABASE_URL")

if DB_MODE == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": os.getenv(
                "DB_ENGINE",
                default="django.db.backends.postgresql",
            ),
            "NAME": os.getenv(
                "DB_NAME",
                default="web_db",
            ),
            "USER": os.getenv(
                "DB_USER",
                default="postgres",
            ),
            "PASSWORD": os.getenv(
                "DB_PASSWORD",
                default="postgres_password",
            ),
            "HOST": os.getenv(
                "DB_HOST",
                default="db",
            ),
            "PORT": os.getenv(
                "DB_PORT",
                default="5432",
            ),
        },
    }
elif DB_MODE == "url" or (
    DB_MODE not in ("postgres", "sqlite") and DATABASE_URL
):
    if (
        DATABASE_URL
        and "?" not in DATABASE_URL
        and "sqlite" not in DATABASE_URL
    ):
        DATABASE_URL += "?sslmode=require"

    DATABASES = {
        "default": dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        ),
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        },
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "ru"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static_dev"]
STATIC_ROOT = BASE_DIR / "static"

if ON_RENDER:
    STATIC_ROOT = BASE_DIR / "staticfiles"

USE_S3_MEDIA = load_bool("USE_S3_MEDIA", False)

if USE_S3_MEDIA:
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_ENDPOINT_URL = os.getenv(
        "AWS_S3_ENDPOINT_URL",
        default="https://storage.yandexcloud.net",
    )

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
            "OPTIONS": {
                "bucket_name": AWS_STORAGE_BUCKET_NAME,
                "endpoint_url": AWS_S3_ENDPOINT_URL,
                "file_overwrite": False,
                "default_acl": None,
            },
        },
        "staticfiles": {
            "BACKEND": (
                "whitenoise.storage.CompressedManifestStaticFilesStorage"
                if ON_RENDER
                else "django.contrib.staticfiles.storage.StaticFilesStorage"
            ),
        },
    }
    MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.storage.yandexcloud.net/"
    MEDIA_ROOT = None
else:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": (
                "whitenoise.storage.CompressedManifestStaticFilesStorage"
                if ON_RENDER
                else "django.contrib.staticfiles.storage.StaticFilesStorage"
            ),
        },
    }
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@resend.dev")

TATSOFT_BASE_URL = os.getenv("TATSOFT_BASE_URL", "")
TATSOFT_TOKEN = os.getenv("TATSOFT_TOKEN", "")