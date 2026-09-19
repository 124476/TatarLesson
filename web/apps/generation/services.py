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
    model = "GigaChat-Pro"

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
        "tatar": [GeminiProvider, GigaChatProvider, GroqProvider],
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
# СПРАВОЧНИК ПО ТАТАРСКОМУ (в контекст для LLM)
# ══════════════════════════════════════════════════════════════════

TATAR_REFERENCE = """СПРАВОЧНИК ТАТАРСКОГО ЯЗЫКА (используй только это!)

СПЕЦИФИЧЕСКИЕ БУКВЫ: ә ө ү җ ң һ
(это НЕ турецкий и НЕ башкирский — не путай!)

ЛИЧНЫЕ МЕСТОИМЕНИЯ:
мин — я, син — ты, ул — он/она, без — мы, сез — вы, алар — они

ПАДЕЖИ (килешләр):
- Именительный:      китап        — книга
- Притяжательный:    китапның     — книги
- Дательный:         китапка      — книге
- Винительный:       китапны      — книгу
- Исходный:          китаптан     — из книги
- Местный:           китапта      — в книге

СПРЯЖЕНИЕ ГЛАГОЛА «укырга» (читать), настоящее время:
мин укыйм — я читаю
син укыйсың — ты читаешь
ул укый — он читает
без укыйбыз — мы читаем
сез укыйсыз — вы читаете
алар укыйлар — они читают

ПРИТЯЖАТЕЛЬНЫЕ АФФИКСЫ (минем китабым — моя книга):
минем китабым, синең китабың, аның китабы,
безнең китабыбыз, сезнең китабыгыз, аларның китабы

ПРОВЕРЕННЫЕ ФРАЗЫ:
Сәлам! — Привет!
Исәнмесез! — Здравствуйте!
Хәерле иртә! — Доброе утро!
Рәхмәт! — Спасибо!
Зинһар — Пожалуйста
Хәлләр ничек? — Как дела?
Яхшы — Хорошо
Минем исемем ... — Меня зовут ...
Мин аңламыйм — Я не понимаю
Кабатлагыз әле — Повторите пожалуйста
Әйе — Да
Юк — Нет
Сау бул! — До свидания!
Сау булыгыз! — До свидания (вежл.)

ЧИСЛА: бер, ике, өч, дүрт, биш, алты, җиде, сигез, тугыз, ун

ПРОВЕРЕННЫЕ СЛОВА:
китап — книга, өй — дом, су — вода, әни — мама, әти — папа,
бала — ребёнок, мәктәп — школа, укучы — ученик, укытучы — учитель,
дус — друг, ипи — хлеб, чәй — чай, сөт — молоко, мәче — кошка,
эт — собака, кош — птица, агач — дерево, чәчәк — цветок,
көн — день, төн — ночь, иртә — утро, кич — вечер, ел — год, ай — месяц

ЗАПРЕЩЕНО (никогда не используй!):
- турецкие слова: merhaba, teşekkür, nasılsın, evet, hayır
- выдуманные слова и идиомы
- фразы «Язмышлы инек», «Сәгатьләрең кайда?»
"""


CHAT_SYSTEM_PROMPT_TEMPLATE = """Ты — Эльмира, тёплый и дружелюбный преподаватель татарского языка в приложении Әйдә укырга!.

⚠️ ГЛАВНЫЕ ПРАВИЛА (никогда не нарушай):
1. Татарский — это НЕ турецкий и НЕ башкирский.
2. НИКОГДА не выдумывай татарские слова и выражения. Если не уверен на 100% — напиши:
   «Точный перевод не уверен, проверьте в словаре».
3. Используй только проверенные слова и фразы из справочника ниже.
4. Если пользователь просит перевести что-то спорное — дай 1-2 безопасных варианта и оговорку.

{reference}

СЛОВА ИЗ НАШЕГО СЛОВАРЯ (приоритетный источник!):
{words_context}

═══════ КАК ОТВЕЧАТЬ ═══════
- Язык ответа: русский (если не просят иначе).
- Кратко и по делу: 2–4 предложения. Без «стен текста».
- Татарские примеры — ВСЕГДА с переводом в скобках или на новой строке.
- Не пиши длинные списки слов — пользователь может спросить ещё.
- Обращайся тепло, по-дружески, изредка уместные эмодзи (🌱 ✨ 📚).
- Пиши живые примеры, а не сухие правила.

═══════ ГРАНИЦЫ ТЕМЫ ═══════
Помогаем только с татарским языком и культурой (лексика, грамматика, произношение,
традиции, праздники, пословицы).
На любые другие темы (рецепты, код, политика, математика и т.п.) отвечай РОВНО:
«Я помогаю только с татарским языком. Спросите что-нибудь о нём 🌱»

═══════ ПРИМЕР ХОРОШЕГО ОТВЕТА ═══════
Вопрос: Как сказать «спасибо» по-татарски?
Ответ: «Спасибо» по-татарски — «Рәхмәт!» [рәхмәт]. Это универсальное слово,
подходит в любой ситуации. Можно усилить: «Зур рәхмәт!» — «Большое спасибо!» ✨
"""


def _get_words_context(limit: int = 60) -> str:
    """Слова из БД для контекста — приоритетный источник для LLM."""
    try:
        from apps.words.models import Word
        words = Word.objects.all().order_by("theme", "tatar")[:limit]
        if not words:
            return "(словарь пока пуст)"
        lines = []
        for w in words:
            extra = f" [{w.transcription}]" if w.transcription else ""
            lines.append(f"- {w.tatar} — {w.russian}{extra}")
        return "\n".join(lines)
    except Exception:
        return "(словарь недоступен)"


CHAT_HISTORY_LIMIT = 10


def _build_chat_messages(history, user_message):
    """Собирает messages для LLM с полным справочником и словарём."""
    words_context = _get_words_context(60)
    system_prompt = CHAT_SYSTEM_PROMPT_TEMPLATE.format(
        reference=TATAR_REFERENCE,
        words_context=words_context,
    )

    messages = [{"role": "system", "content": system_prompt}]
    for msg in history[-CHAT_HISTORY_LIMIT:]:
        messages.append({
            "role": msg["role"],
            "content": msg["content"],
        })
    messages.append({"role": "user", "content": user_message})
    return messages


def chat_with_tatar_ai(history: list[dict], user_message: str) -> str | None:
    """Чат с AI по татарскому. Для Gemini system склеивается в единый prompt."""
    messages = _build_chat_messages(history, user_message)

    client = LLMClient(profile="tatar")

    def attempt(provider):
        if provider.name == "Gemini":
            parts = []
            for m in messages:
                prefix = {
                    "system": "ИНСТРУКЦИЯ",
                    "user": "Пользователь",
                    "assistant": "Эльмира",
                }.get(m["role"], m["role"])
                parts.append(f"{prefix}:\n{m['content']}")
            parts.append("Эльмира:")
            prompt = "\n\n".join(parts)
            return provider.call(prompt, max_tokens=700, json_mode=False)

        return _call_with_messages(provider, messages, max_tokens=700)

    return client._try_all(attempt)


def _call_with_messages(provider, messages, max_tokens=700):
    """Универсальный вызов для OpenAI-совместимых (Groq) и GigaChat."""
    import requests

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
                "temperature": 0.35,
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
                "temperature": 0.35,
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
# ГЕНЕРАЦИЯ БЛОКОВ УРОКА
# ══════════════════════════════════════════════════════════════════

def _fetch_lesson_words(theme: str, count: int, use_dictionary: bool) -> list[dict]:
    """Слова для урока: сначала из БД, потом добираем через LLM."""
    from apps.words.models import Word
    from django.db.models import Q

    words: list[dict] = []
    seen: set[str] = set()

    def _push(tatar: str, russian: str, ex_tt: str = "", ex_ru: str = ""):
        key = (tatar or "").strip().lower()
        if not key or key in seen:
            return
        seen.add(key)
        words.append({
            "tatar": tatar.strip(),
            "russian": russian.strip(),
            "example_tt": (ex_tt or "").strip(),
            "example_ru": (ex_ru or "").strip(),
        })

    if use_dictionary:
        db_qs = (
            Word.objects
            .filter(Q(theme=theme) | Q(russian__icontains=theme))
            .values("tatar", "russian", "example_tt", "example_ru")[:count]
        )
        for w in db_qs:
            _push(w["tatar"], w["russian"], w["example_tt"], w["example_ru"])

    if len(words) < count:
        need = count - len(words)
        generated = generate_words(theme=theme, n=need) or []
        for g in generated:
            _push(
                g.get("tatar", ""),
                g.get("russian", ""),
                g.get("example_tt", ""),
                g.get("example_ru", ""),
            )

    return words


BLOCK_POINTS = {
    "audio": 10,
    "translate": 10,
    "build": 15,
    "quick": 10,
    "gap": 10,
    "pairs": 20,
}

def _make_gap_sentence(w: dict) -> str:
    """Строит предложение с пропуском ___ из example_tt."""
    ex = (w.get("example_tt") or "").strip()
    tatar = (w.get("tatar") or "").strip()

    if ex and tatar:
        if tatar in ex:
            return ex.replace(tatar, "___", 1)
        idx = ex.lower().find(tatar.lower())
        if idx >= 0:
            return ex[:idx] + "___" + ex[idx + len(tatar):]
        return f"___ {ex}"
    if ex:
        return ex
    return "___"


def generate_lesson_blocks(
    theme: str,
    types: list[str] | None = None,
    count: int = 8,
    use_dictionary: bool = True,
) -> list[dict] | None:
    """
    Собирает блоки для урока по теме.
    Возвращает список {type, points, config} — как в lesson_builder.
    """
    valid = {"audio", "translate", "build", "quick", "gap", "pairs"}
    if not types:
        types = ["translate", "build"]
    types = [t for t in types if t in valid]
    if not types:
        types = ["translate"]

    count = max(3, min(int(count), 20))

    # Один слот забирает pairs, если он в выбранных типах
    use_pairs = "pairs" in types
    non_pairs = [t for t in types if t != "pairs"]

    # Слов нужно примерно столько же, сколько блоков + запас на pairs
    words_needed = count + (4 if use_pairs else 0)
    words = _fetch_lesson_words(theme, words_needed, use_dictionary)

    min_words = max(3, count) if not use_pairs else 4
    if len(words) < min_words:
        return None

    blocks: list[dict] = []

    # Сначала обычные блоки (round-robin по выбранным типам)
    n_regular = count - (1 if use_pairs else 0)
    if n_regular < 1:
        n_regular = 1

    regular_types = non_pairs or ["translate"]
    for i in range(n_regular):
        if i >= len(words):
            break
        w = words[i]
        t = regular_types[i % len(regular_types)]

        if t == "build":
            config = {
                "word": w["tatar"],  # правильный ответ (собирается)
                "correct": w["russian"],  # подсказка
            }
        elif t == "gap":
            config = {
                "sentence": _make_gap_sentence(w),  # "Мин ___ укыйм."
                "correct": w["tatar"],  # ответ
                "hint": w["russian"],  # перевод предложения
                "word": w["tatar"],  # legacy
            }
        else:
            config = {
                "word": w["tatar"],
                "correct": w["russian"],
            }

        blocks.append({
            "type": t,
            "points": BLOCK_POINTS.get(t, 10),
            "config": config,
        })

    # Пары — один блок с 4–5 словами
    if use_pairs:
        pair_words = words[:5]
        if len(pair_words) >= 3:
            blocks.append({
                "type": "pairs",
                "points": BLOCK_POINTS["pairs"],
                "config": {
                    "pairs": [[w["tatar"], w["russian"]] for w in pair_words],
                },
            })

    return blocks or None
