import json

from django import template

register = template.Library()


@register.filter
def format_answer(submission, max_len=80):
    """
    Превращает Submission.answer в человекочитаемую строку
    с учётом типа задачи.

    pairs:            [["Акыл","Ум"],…]  →  "Акыл → Ум; Арыслан → Лев; …"
    multiple_choice:  ["a","b"]          →  "a, b"
    всё остальное:    как есть
    """
    if not submission:
        return ""

    task = getattr(submission, "task", None)
    task_type = getattr(task, "task_type", "") if task else ""
    raw = (submission.answer or "").strip()

    formatted = raw

    if task_type == "pairs":
        try:
            pairs = json.loads(raw)
        except (ValueError, TypeError):
            pairs = None
        if isinstance(pairs, list):
            parts = []
            for p in pairs:
                if isinstance(p, list) and len(p) == 2:
                    left  = str(p[0]).strip()
                    right = str(p[1]).strip()
                    if left or right:
                        parts.append(f"{left} → {right}")
            if parts:
                formatted = "; ".join(parts)

    elif task_type == "multiple_choice":
        try:
            items = json.loads(raw)
        except (ValueError, TypeError):
            items = None
        if isinstance(items, list):
            formatted = ", ".join(str(x).strip() for x in items if str(x).strip())

    if max_len and len(formatted) > int(max_len):
        formatted = formatted[: int(max_len) - 1].rstrip() + "…"

    return formatted
