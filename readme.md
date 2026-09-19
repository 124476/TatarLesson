# Әйдә укырга! — Веб-платформа для управления событиями и новостями

**Сайт:** https://tatarlesson.onrender.com/

---

## Скриншоты

<table>
  <tr align="center">
    <td colspan="2">
      <img src="images/screenshot1.png" width="100%" alt="Главная страница" /><br>
      <em>Страница о нас</em>
    </td>
  </tr>
  <tr>
    <td align="center">
      <img src="images/screenshot2.png" width="500" alt="Чат поддержки" /><br>
      <em>Чат поддержки</em>
    </td>
    <td align="center">
      <img src="images/screenshot3.png" width="500" alt="Регистрация" /><br>
      <em>Регистрация</em>
    </td>
  </tr>
  <tr>
    <td align="center">
      <img src="images/screenshot4.png" width="500" alt="Уведомления" /><br>
      <em>Уведомления</em>
    </td>
    <td align="center">
      <img src="images/screenshot5.png" width="500" alt="Профиль" /><br>
      <em>Личный профиль</em>
    </td>
  </tr>
</table>

---

## Возможности

- **Личные профили** – редактирование профиля, аватарки, настройки темы
- **Уведомления в реальном времени** – long polling, маркировка прочитанных
- **Чат поддержки** – встроенный виджет с историей сообщений
- **Тёмная/светлая тема** – переключение с сохранением в localStorage
- **OAuth2-аутентификация** – через Яндекс, GitHub, Google
- **Административная панель** – управление контентом через Django Admin

---

## Тестовый доступ

Для ознакомления с функционалом приложения вы можете использовать тестовую учётную запись:

| **Логин** | **Пароль** | **Роль** |
|-----------|------------|----------|
| `1`       | `1`        | Админ    | 

---

## Технологии

- **Backend:** Django 5.1, Python 3.12
- **База данных:** PostgreSQL (поддержка SQLite и внешних URL)
- **Frontend:** Bootstrap 5, CSS-переменные, JavaScript (vanilla)
- **Хранение медиа:** локальное или Yandex Cloud Object Storage (S3)
- **Аутентификация:** django-allauth / social-auth (Яндекс, GitHub, Google)
- **Деплой:** Docker, Render

---

## Ссылки

- **Репозиторий проекта:** [GitHub](https://github.com/124476/TatarLesson)
- **Сайт:** https://tatarlesson.onrender.com/

---

> **Примечание:** Инструкцию по запуску проекта смотрите в файле [setup.md](setup.md).

---

**Әйдә укырга!** — интерактивная платформа для изучения татарского языка: учитель собирает уроки из блоков, ученики занимаются в классе или самостоятельно, соревнуются в дуэлях и учат новое слово каждый день.