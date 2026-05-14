"""
Скрипт для генерации описания PR через OpenRouter AI API.

Используется в GitHub Actions workflow ai-pr-description.yml.
Сохраняет результат в /tmp/pr_description.txt.
"""

import json
import os
import urllib.request

API_KEY = os.environ.get("OPENAI_API_KEY", "")
DIFF_B64 = os.environ.get("DIFF_B64", "")

SYSTEM_MSG = (
    "Ты — ассистент, анализирующий изменения кода в Pull Request. "
    "Отвечай на русском языке."
)

USER_MSG = f"""Проанализируй git diff (base64 ниже).

1. Какие файлы изменены?
2. Общая цель: баги / новый функционал / рефакторинг / безопасность?
3. Есть ли миграции БД, изменения API, новые зависимости?

Формат ответа:

## Описание изменений

### Кратко
(1-2 предложения)

### Список изменений
- файл: что изменено

### Важные замечания
(миграции, API, зависимости)

Дифф:
{DIFF_B64}"""

REQUEST_BODY = {
    "model": "qwen/qwen3-coder",
    "messages": [
        {"role": "system", "content": SYSTEM_MSG},
        {"role": "user", "content": USER_MSG},
    ],
    "temperature": 0.3,
    "max_tokens": 2000,
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
        content = f"Ошибка при генерации описания: {e}"

    with open("/tmp/pr_description.txt", "w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    main()
