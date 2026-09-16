__all__ = ()

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
        )
        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "form-input",
                },
            ),
            "first_name": forms.TextInput(
                attrs={
                    "class": "form-input",
                },
            ),
            "last_name": forms.TextInput(
                attrs={
                    "class": "form-input",
                },
            ),
        }

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if (
            User.objects.filter(username=username)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise ValidationError("Пользователь с таким именем уже существует")

        return username


class AvatarUploadForm(forms.Form):
    avatar = forms.ImageField(
        label="Выберите фото",
        widget=forms.FileInput(
            attrs={
                "accept": "image/*",
            },
        ),
    )


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "Email",
            },
        ),
        error_messages={
            "invalid": "Введите правильный email адрес.",
            "required": "Email обязателен.",
        },
    )
    username = forms.CharField(
        label="Имя пользователя",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Имя пользователя",
            },
        ),
    )
    password1 = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Пароль",
            },
        ),
    )
    password2 = forms.CharField(
        label="Подтверждение пароля",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Подтверждение пароля",
            },
        ),
    )
    error_messages = {
        "password_mismatch": "Пароли не совпадают.",
    }

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if User.objects.filter(username=username).exists():
            raise ValidationError("Пользователь с таким именем уже существует")

        return username

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise ValidationError("Пользователь с таким email уже существует")

        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()

        return user


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Имя пользователя или Email",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Имя пользователя или Email",
            },
        ),
    )
    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Пароль",
            },
        ),
    )
    error_messages = {
        "invalid_login": "Неверное имя пользователя или пароль.",
        "inactive": "Этот аккаунт неактивен.",
    }

    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if username and password:
            try:
                user = User.objects.get(email=username)
                username = user.username
            except User.DoesNotExist:
                pass

            self.cleaned_data["username"] = username

        return super().clean()


class PasswordChangeForm(forms.Form):
    old_password = forms.CharField(
        label="Текущий пароль",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Введите текущий пароль",
            },
        ),
        required=False,
    )
    new_password1 = forms.CharField(
        label="Новый пароль",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Введите новый пароль",
            },
        ),
    )
    new_password2 = forms.CharField(
        label="Подтверждение пароля",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Подтвердите новый пароль",
            },
        ),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        if not user.has_usable_password():
            self.fields["old_password"].widget = forms.HiddenInput()
            self.fields["old_password"].required = False

    def clean_old_password(self):
        old_password = self.cleaned_data.get("old_password")

        if not self.user.has_usable_password():
            return old_password

        if not old_password:
            raise forms.ValidationError("Введите текущий пароль")

        if not self.user.check_password(old_password):
            raise forms.ValidationError("Неверный текущий пароль")

        return old_password

    def clean_new_password2(self):
        password1 = self.cleaned_data.get("new_password1")
        password2 = self.cleaned_data.get("new_password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Пароли не совпадают")

        if len(password1) < 8:
            raise forms.ValidationError(
                "Пароль должен содержать минимум 8 символов",
            )

        return password2

    def save(self):
        new_password = self.cleaned_data.get("new_password1")
        self.user.set_password(new_password)
        self.user.save()
        return self.user


class EmailChangeForm(forms.Form):
    new_email = forms.EmailField(
        label="Новый email",
        widget=forms.EmailInput(
            attrs={
                "class": "form-input",
                "placeholder": "Введите новый email",
            },
        ),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_new_email(self):
        new_email = self.cleaned_data.get("new_email")
        if (
            User.objects.filter(email=new_email)
            .exclude(id=self.user.id)
            .exists()
        ):
            raise forms.ValidationError("Этот email уже используется")

        if new_email == self.user.email:
            raise forms.ValidationError("Новый email совпадает с текущим")

        return new_email
