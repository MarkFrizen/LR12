"""
Скрипт для AI Code Review через OpenRouter API.

Используется в GitHub Actions workflow ai-pr-description.yml.
Читает git diff из /tmp/git_diff.b64 (записан на шаге 2).
Сохраняет результат в /tmp/pr_review.txt.
"""

import json
import os
import urllib.request

API_KEY = os.environ.get("OPENAI_API_KEY", "")

DIFF_PATH = "/tmp/git_diff.b64"
if not os.path.exists(DIFF_PATH):
    raise FileNotFoundError(
        f"Файл с git diff не найден: {DIFF_PATH}. "
        "Убедитесь, что шаг 'Get git diff' выполнен."
    )
with open(DIFF_PATH, "r") as f:
    DIFF_B64 = f.read().strip()

SYSTEM_MSG = (
    "Ты — senior Python-разработчик, проводящий code review "
    "маркетплейса на FastAPI + SQLAlchemy. Отвечай на русском языке. "
    "Будь строг и предметен. Каждую найденную проблему сопровождай "
    "фрагментом кода и рекомендацией."
)

USER_MSG = f"""Проверь код из git diff (base64 ниже) на типовые ошибки маркетплейса.

Особое внимание удели:

1. **Расчёт комиссии без учёта скидки** — комиссия берётся от полной цены, а не от цены со скидкой.
2. **Доступ к заказам без проверки роли продавца** — эндпоинты заказов, где любой пользователь может смотреть/менять чужие заказы (отсутствие Depends(require_seller) / require_buyer / ownership).
3. **Невалидированная цена** — price допускает отрицательные значения, отсутствует Field(gt=0) в Pydantic.
4. **Незакрытая транзакция** — async-сессия не закрывается при исключении, commit/rollback не сбалансированы.
5. **N+1 запросы** — циклы с отдельными запросами к БД вместо JOIN или selectinload.
6. **Утечка чувствительных данных** — хэш пароля, email, телефон в логах или ответах API.
7. **Отсутствие idempotency-key** — повторный POST создаёт дубликаты заказов/платежей.

Формат ответа — таблица на русском:

## Результат AI Code Review

| # | Файл | Проблема | Серьёзность | Рекомендация |
|---|------|----------|-------------|--------------|
| 1 | `app/services/x.py:42` | Описание | 🔴 / 🟠 / 🟡 | Как исправить |

Если критических проблем нет — напиши:

## Результат AI Code Review

✅ **Критических проблем не найдено.**

Дифф:
{DIFF_B64}"""

REQUEST_BODY = {
    "model": "qwen/qwen3-coder",
    "messages": [
        {"role": "system", "content": SYSTEM_MSG},
        {"role": "user", "content": USER_MSG},
    ],
    "temperature": 0.2,
    "max_tokens": 3000,
}


def main() -> None:
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(REQUEST_BODY).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.load(resp)
            content = data["choices"][0]["message"]["content"]
    except Exception as e:
        content = f"Ошибка при code review: {e}"

    with open("/tmp/pr_review.txt", "w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    main()
