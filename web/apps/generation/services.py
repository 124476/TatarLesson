"""Единый клиент для LLM с fallback-цепочкой."""
import json
import logging
import re
import time
import uuid

import requests
import urllib3

from django.conf import settings

logger = logging.getLogger(__name__)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ══════════════════════════════════════════════════════════════════
# УТИЛИТЫ
# ══════════════════════════════════════════════════════════════════

# Русские/типографские кавычки → ASCII
_QUOTE_MAP = {
    "«": '"', "»": '"',
    "“": '"', "”": '"',
    "„": '"', "‟": '"',
    "‘": "'", "’": "'",
    "′": "'", "″": '"',
    "–": "-", "—": "-",  # длинное тире → дефис (для JSON-ключей не критично)
}


def _normalize_quotes(text: str) -> str:
    """Заменяет типографские кавычки на ASCII."""
    for src, dst in _QUOTE_MAP.items():
        text = text.replace(src, dst)
    return text


def _extract_json(text: str):
    """
    Достаёт JSON из ответа LLM.
    Убирает markdown-обёртку, чинит кавычки, парсит.
    Возвращает dict | list | None.
    """
    if not text:
        return None

    s = text.strip()

    # Убираем markdown
    if s.startswith("```json"):
        s = s[7:]
    elif s.startswith("```"):
        s = s[3:]
    if s.endswith("```"):
        s = s[:-3]
    s = s.strip()

    # Чиним кавычки
    s = _normalize_quotes(s)

    # Пробуем распарсить как есть
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass

    # Пробуем найти JSON-массив/объект регуляркой
    for pattern in (r"\[.*\]", r"\{.*\}"):
        m = re.search(pattern, s, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                continue

    return None


# ══════════════════════════════════════════════════════════════════
# ПРОВАЙДЕРЫ
# ══════════════════════════════════════════════════════════════════

class BaseProvider:
    name = "base"
    model = ""

    def call(self, prompt: str, max_tokens: int = 1000,
             json_mode: bool = False) -> str:
        raise NotImplementedError


class GigaChatProvider(BaseProvider):
    """GigaChat (Сбер). Знает татарский. Медленный, но точный."""
    name = "GigaChat"
    model = "GigaChat"

    _token = None
    _expires_at = 0

    @classmethod
    def _get_token(cls):
        now = time.time()
        if cls._token and now < cls._expires_at - 60:
            return cls._token

        auth_key = getattr(settings, "GIGACHAT_AUTH_KEY", "")
        if not auth_key:
            raise RuntimeError("GIGACHAT_AUTH_KEY не задан в settings")

        r = requests.post(
            "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "RqUID": str(uuid.uuid4()),
                "Authorization": f"Basic {auth_key}",
            },
            data={"scope": "GIGACHAT_API_PERS"},
            verify=False,
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        cls._token = data["access_token"]
        cls._expires_at = data.get("exp", now + 1800)
        return cls._token

    def call(self, prompt, max_tokens=1000, json_mode=False):
        token = self._get_token()

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": max_tokens,
        }
        # У GigaChat есть режим JSON
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        r = requests.post(
            "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
            },
            json=payload,
            verify=False,
            timeout=90,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


class GeminiProvider(BaseProvider):
    """Gemini 3.5 Flash-Lite. Стабильный, быстрый. Знает базовый татарский."""
    name = "Gemini"
    model = "gemini-3.5-flash-lite"

    def call(self, prompt, max_tokens=1000, json_mode=False):
        api_key = getattr(settings, "GEMINI_API_KEY", "")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY не задан в settings")

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": max_tokens,
            },
        }
        if json_mode:
            payload["generationConfig"][
                "responseMimeType"] = "application/json"

        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={api_key}",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=90,
        )
        r.raise_for_status()
        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


class GroqProvider(BaseProvider):
    """Groq + gpt-oss-120b. Самый быстрый. Reasoning-модель."""
    name = "Groq"
    model = "openai/gpt-oss-120b"

    def call(self, prompt, max_tokens=1000, json_mode=False):
        api_key = getattr(settings, "GROQ_API_KEY", "")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY не задан в settings")

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": max_tokens,
            # Отключаем "размышления" — иначе content иногда пустой
            "reasoning_effort": "low",
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=90,
        )
        r.raise_for_status()
        data = r.json()
        choice = data["choices"][0]["message"]
        # Fallback: если content пустой — берём reasoning_content
        return choice.get("content") or choice.get("reasoning_content", "")


# ══════════════════════════════════════════════════════════════════
# ГЛАВНЫЙ КЛИЕНТ
# ══════════════════════════════════════════════════════════════════

class LLMClient:
    """
    Универсальный клиент с fallback.

    Использование:
        client = LLMClient()
        result = client.generate_json(prompt)
        text = client.generate_text(prompt)
    """

    # Провайдеры в порядке приоритета
    #   Gemini — лучший по JSON и стабильности
    #   GigaChat — лучший по татарскому
    #   Groq — быстрый fallback
    PROVIDERS = [
        GeminiProvider,
        GigaChatProvider,
        GroqProvider,
    ]

    # Профили: для разных задач — разный порядок провайдеров
    PROFILES = {
        "tatar": [GigaChatProvider, GeminiProvider, GroqProvider],
        "json": [GeminiProvider, GigaChatProvider, GroqProvider],
        "fast": [GroqProvider, GeminiProvider, GigaChatProvider],
    }

    def __init__(self, profile: str = "json"):
        provider_classes = self.PROFILES.get(profile, self.PROVIDERS)
        self.providers = [p() for p in provider_classes]
        self.last_provider = None
        self.last_error = None

    def _try_all(self, method, *args, **kwargs):
        """Пробует всех провайдеров по очереди."""
        errors = []
        for provider in self.providers:
            try:
                result = method(provider, *args, **kwargs)
                if result:  # не пустой
                    self.last_provider = provider.name
                    return result
                errors.append(f"{provider.name}: пустой ответ")
            except Exception as e:
                err = f"{provider.name}: {type(e).__name__}: {str(e)[:120]}"
                logger.warning("LLM fallback: %s", err)
                errors.append(err)

        self.last_error = "; ".join(errors)
        logger.error("Все провайдеры упали: %s", self.last_error)
        return None

    def generate_text(self, prompt: str, max_tokens: int = 1000) -> str | None:
        """Возвращает текстовый ответ."""
        return self._try_all(
            lambda p: p.call(prompt, max_tokens=max_tokens, json_mode=False),
        )

    def generate_json(self, prompt: str, max_tokens: int = 2000):
        """
        Возвращает распарсенный JSON (dict | list) или None.
        Автоматически чистит кавычки и markdown.
        """

        def attempt(provider):
            raw = provider.call(prompt, max_tokens=max_tokens, json_mode=True)
            return _extract_json(raw)

        return self._try_all(attempt)


# ══════════════════════════════════════════════════════════════════
# ГОТОВЫЕ ФУНКЦИИ ДЛЯ СЕРВИСА
# ══════════════════════════════════════════════════════════════════

WORDS_PROMPT = """Ты — лингвист-татаролог. Сгенерируй {n} татарских слов по теме "{theme}".

Верни СТРОГО JSON-массив без markdown. Используй ТОЛЬКО прямые двойные кавычки ASCII ("), не используй «» и "".
Формат каждого элемента:
{{"tatar": "...", "russian": "...", "transcription": "...", "example_tt": "...", "example_ru": "..."}}

Требования:
- tatar — татарское слово на кириллице
- russian — русский перевод
- transcription — латиница с диакритикой (ə, ö, ü, ğ, ñ, ç)
- example_tt — короткое предложение на татарском
- example_ru — перевод предложения на русский

Отвечай ТОЛЬКО JSON, без пояснений."""


def generate_words(theme: str, n: int = 5) -> list[dict] | None:
    """Генерирует N слов по теме."""
    client = LLMClient(profile="tatar")
    prompt = WORDS_PROMPT.format(n=n, theme=theme)
    result = client.generate_json(prompt, max_tokens=2000)

    if not isinstance(result, list):
        return None

    # Валидация структуры
    cleaned = []
    for item in result:
        if not isinstance(item, dict):
            continue
        if not item.get("tatar") or not item.get("russian"):
            continue
        cleaned.append({
            "tatar": str(item.get("tatar", "")).strip(),
            "russian": str(item.get("russian", "")).strip(),
            "transcription": str(item.get("transcription", "")).strip(),
            "example_tt": str(item.get("example_tt", "")).strip(),
            "example_ru": str(item.get("example_ru", "")).strip(),
        })
    return cleaned or None


DISTRACTORS_PROMPT = """Правильный ответ: "{correct}".
Тема: "{theme}".
Придумай 3 неправильных, но правдоподобных русских варианта.

Верни СТРОГО JSON-массив из 3 строк. Только прямые кавычки ASCII (").
Пример: ["вариант1", "вариант2", "вариант3"]
Отвечай ТОЛЬКО JSON."""


def generate_distractors(correct: str, theme: str = "общее") -> list[
                                                                    str] | None:
    """Генерирует 3 неправильных варианта для теста."""
    client = LLMClient(profile="json")
    prompt = DISTRACTORS_PROMPT.format(correct=correct, theme=theme)
    result = client.generate_json(prompt, max_tokens=200)

    if not isinstance(result, list):
        return None
    return [str(x).strip() for x in result if str(x).strip()][:3]


EXPLAIN_PROMPT = """Ты — преподаватель татарского языка.
Объясни кратко и понятно (не более 3 предложений) следующий вопрос:

{question}

Если вопрос НЕ про татарский язык (лексика, грамматика, культура, перевод) —
ответь ровно так: "Я помогаю только с татарским языком."

Отвечай на русском языке."""


def explain_tatar(question: str) -> str | None:
    """Объяснение по татарскому языку. Отказывает на сторонние темы."""
    client = LLMClient(profile="tatar")
    prompt = EXPLAIN_PROMPT.format(question=question)
    return client.generate_text(prompt, max_tokens=400)

# ══════════════════════════════════════════════════════════════════
# ЧАТ С AI ПО ТАТАРСКОМУ
# ══════════════════════════════════════════════════════════════════

CHAT_SYSTEM_PROMPT_TEMPLATE = """Ты — дружелюбный ассистент по татарскому языку и культуре в приложении TatarLesson.

ТВОЯ ЗАДАЧА:
- Помогать с переводом (русский ↔ татарский)
- Объяснять грамматику татарского языка (падежи, аффиксы, времена)
- Рассказывать о татарской культуре, традициях, праздниках
- Помогать учить слова, транскрипцию и произношение

КРИТИЧЕСКИ ВАЖНО ПРО ТАТАРСКИЙ ЯЗЫК:
- Татарский — это НЕ турецкий и НЕ башкирский. Не путай!
- Татарский алфавит: ә ө ү җ ң һ (это специфические буквы)
- Используй ТОЛЬКО те татарские слова, в которых уверен на 100%
- НЕ выдумывай слова и фразы. Если не знаешь — скажи "Точный перевод не уверен, проверьте в словаре"
- Если фраза звучит странно (как в турецком) — НЕ используй её
- НЕ придумывай идиомы и устойчивые выражения

ПРОВЕРЕННЫЕ СЛОВА ИЗ НАШЕГО СЛОВАРЯ (используй в первую очередь):
{words_context}

ПРАВИЛЬНЫЕ ПРИМЕРЫ (запомни их):
- Приветствие: "Сәлам!" или "Исәнмесез!" (официальное)
- Спасибо: "Рәхмәт!"
- Как дела: "Хәлләр ничек?" 
- Меня зовут...: "Минем исемем..."
- Я не понимаю: "Мин аңламыйм"
- Книга: "китап", дом: "өй", вода: "су", мама: "әни", папа: "әти"

НЕПРАВИЛЬНЫЕ ПРИМЕРЫ (НЕ используй!):
- "Язмышлы инек" — так не говорят
- "Сәгатьләрең кайда?" — не говорят
- "Нәрсә кызыксынды?" — грамматически неверно
- Любые турецкие слова (merhaba, teşekkür, nasılsın и т.д.)

ЖЁСТКИЕ ОГРАНИЧЕНИЯ ПО ТЕМЕ:
- Отвечай ТОЛЬКО на вопросы про татарский язык и культуру
- На любые другие темы (рецепты, программирование, политика) отвечай ровно:
  "Я помогаю только с татарским языком. Спросите что-нибудь о нём 🌱"

ФОРМАТ ОТВЕТА:
- Отвечай на русском
- Кратко: 2-4 предложения (не больше!)
- Пример на татарском — с переводом на русский
- НЕ пиши длинные списки слов или фраз
- Будь дружелюбным, но не навязчивым
"""


def _get_words_context(limit: int = 40) -> str:
    """Загружает слова из БД для контекста."""
    try:
        from apps.words.models import Word
        words = Word.objects.all()[:limit]
        if not words:
            return "(словарь пока пуст)"
        return "\n".join(
            f"- {w.tatar} — {w.russian}" + (f" [{w.transcription}]" if w.transcription else "")
            for w in words
        )
    except Exception:
        return "(словарь недоступен)"


def _build_chat_messages(history, user_message):
    """Собирает messages для LLM."""
    from apps.words.models import Word

    # Берём слова из БД (до 40)
    words = Word.objects.all()[:40]
    words_context = "\n".join(
        f"- {w.tatar} — {w.russian}" + (f" [{w.transcription}]" if w.transcription else "")
        for w in words
    ) or "(словарь пока пуст)"

    system_prompt = CHAT_SYSTEM_PROMPT_TEMPLATE.format(words_context=words_context)

    messages = [{"role": "system", "content": system_prompt}]
    for msg in history[-CHAT_HISTORY_LIMIT:]:
        messages.append({
            "role": msg["role"],
            "content": msg["content"],
        })
    messages.append({"role": "user", "content": user_message})
    return messages


CHAT_HISTORY_LIMIT = 10  # последних сообщений в контекст


def chat_with_tatar_ai(history: list[dict], user_message: str) -> str | None:
    """
    Отправляет сообщение в LLM с историей.
    history: [{"role": "user"|"assistant", "content": "..."}]
    Возвращает текст ответа или None.
    """
    messages = _build_chat_messages(history, user_message)

    client = LLMClient(profile="tatar")

    def attempt(provider):
        # Провайдеры по-разному принимают messages.
        # У GigaChat/Groq — массив messages, у Gemini — склеиваем.
        if provider.name == "Gemini":
            # Склеиваем всё в один prompt
            parts = []
            for m in messages:
                prefix = {
                    "system": "ИНСТРУКЦИЯ",
                    "user": "Пользователь",
                    "assistant": "Ассистент",
                }.get(m["role"], m["role"])
                parts.append(f"{prefix}:\n{m['content']}")
            parts.append("Ассистент:")
            prompt = "\n\n".join(parts)
            return provider.call(prompt, max_tokens=600, json_mode=False)

        # GigaChat и Groq принимают messages напрямую
        return _call_with_messages(provider, messages, max_tokens=600)

    return client._try_all(attempt)


def _call_with_messages(provider, messages, max_tokens=600):
    """Универсальный вызов для OpenAI-совместимых (Groq) и GigaChat."""
    import requests
    import uuid as _uuid
    import time as _time

    if provider.name == "GigaChat":
        token = provider._get_token()
        r = requests.post(
            "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
            },
            json={
                "model": provider.model,
                "messages": messages,
                "temperature": 0.5,
                "max_tokens": max_tokens,
            },
            verify=False,
            timeout=90,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    if provider.name == "Groq":
        api_key = getattr(settings, "GROQ_API_KEY", "")
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": provider.model,
                "messages": messages,
                "temperature": 0.5,
                "max_tokens": max_tokens,
                "reasoning_effort": "low",
            },
            timeout=90,
        )
        r.raise_for_status()
        data = r.json()
        choice = data["choices"][0]["message"]
        return choice.get("content") or choice.get("reasoning_content", "")

    raise RuntimeError(f"Provider {provider.name} не поддерживает chat")


# ══════════════════════════════════════════════════════════════════
# ГЕНЕРАЦИЯ ЗАДАЧ ДЛЯ СОРЕВНОВАНИЙ
# ══════════════════════════════════════════════════════════════════

COMPETITION_TASKS_PROMPT = """Ты — методист, создающий задания для соревнований по татарскому языку.

Создай {n} задач на тему "{theme}".
Используй ТОЛЬКО эти слова (татарский — русский):
{words_block}

Допустимые типы задач: {types}
Распредели задачи равномерно по этим типам.

Верни СТРОГО JSON-массив задач без markdown. Используй ТОЛЬКО прямые двойные кавычки ASCII (").
Формат задачи зависит от типа:

Тип "text" (текстовый ответ):
{{"task_type":"text","title":"Переведи слово","statement":"Переведи на татарский: дом","correct_answer":"өй","points":100,"max_attempts":5,"options":[],"build_word":"","build_hint":"","pairs":[],"voice_text":""}}

Тип "choice" (один вариант из 4):
{{"task_type":"choice","title":"Выбери перевод","statement":"Как переводится 'дом'?","correct_answer":"өй","options":[{{"text":"өй","is_correct":true}},{{"text":"су","is_correct":false}},{{"text":"урман","is_correct":false}},{{"text":"яңгыр","is_correct":false}}],"points":100,"max_attempts":5,"build_word":"","build_hint":"","pairs":[],"voice_text":""}}
ВАЖНО: правильный вариант — ровно один, всего 4 варианта. Дистракторы — реальные татарские слова с других тем.

Тип "build" (собери слово):
{{"task_type":"build","title":"Собери слово","statement":"Собери татарское слово, означающее 'дом'","build_word":"өй","build_hint":"дом","correct_answer":"","options":[],"pairs":[],"voice_text":"","points":100,"max_attempts":5}}

Тип "pairs" (найди пару — минимум 3 пары):
{{"task_type":"pairs","title":"Найди пары","statement":"Соедини татарские слова с русскими переводами","pairs":[["өй","дом"],["су","вода"],["урман","лес"]],"correct_answer":"","options":[],"build_word":"","build_hint":"","voice_text":"","points":100,"max_attempts":3}}

Тип "voice" (голосовой ответ):
{{"task_type":"voice","title":"Произнеси слово","statement":"Произнеси слово вслух: өй","voice_text":"өй","correct_answer":"өй","options":[],"build_word":"","build_hint":"","pairs":[],"points":100,"max_attempts":5}}

Требования:
- points: 100 для обычных, 150 для pairs, 80 для build
- max_attempts: 5 (3 для pairs)
- statement, title — на русском
- Татарские слова — только из предоставленного списка
- Отвечай ТОЛЬКО JSON-массивом, без пояснений и markdown
"""


def generate_competition_tasks(
    theme: str,
    n_tasks: int = 5,
    task_types: list[str] | None = None,
    words: list[dict] | None = None,
) -> list[dict] | None:
    """
    Генерирует задачи для соревнования.
    words — список {tatar, russian}. Если не передан — генерируется через generate_words.
    """
    if not task_types:
        task_types = ["text", "choice", "build"]

    # Слова
    if not words:
        words = generate_words(theme=theme, n=15) or []
    if len(words) < 5:
        return None

    # Собираем блок слов
    words_block = "\n".join(
        f"- {w['tatar']} — {w['russian']}" for w in words
    )
    types_str = ", ".join(task_types)

    prompt = COMPETITION_TASKS_PROMPT.format(
        n=n_tasks,
        theme=theme,
        words_block=words_block,
        types=types_str,
    )

    client = LLMClient(profile="json")
    result = client.generate_json(prompt, max_tokens=4000)

    if not isinstance(result, list):
        return None

    # Валидация
    valid_types = {"text", "choice", "multiple_choice", "build", "pairs", "voice"}
    cleaned = []
    for t in result:
        if not isinstance(t, dict):
            continue
        ttype = t.get("task_type")
        if ttype not in valid_types:
            continue
        if not t.get("title") or not t.get("statement"):
            continue

        cleaned.append({
            "title": str(t.get("title", "")).strip()[:255],
            "statement": str(t.get("statement", "")).strip(),
            "task_type": ttype,
            "correct_answer": str(t.get("correct_answer", "")).strip(),
            "options": t.get("options", []) if isinstance(t.get("options"), list) else [],
            "build_word": str(t.get("build_word", "")).strip(),
            "build_hint": str(t.get("build_hint", "")).strip(),
            "pairs": t.get("pairs", []) if isinstance(t.get("pairs"), list) else [],
            "voice_text": str(t.get("voice_text", "")).strip(),
            "points": int(t.get("points", 100)),
            "max_attempts": int(t.get("max_attempts", 5)),
        })

    return cleaned or None
