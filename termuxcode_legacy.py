import os
import json
import re
import time
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

# =========================
# CONFIG
# =========================

API_KEY = os.environ.get("GEMINI_API_KEY")

if not API_KEY:
    print("❌ GEMINI_API_KEY не найден.")
    print('Выполни: export GEMINI_API_KEY="твой_ключ"')
    raise SystemExit(1)

MODEL = "gemini-3.8-flash"

ROOT = Path.cwd().resolve()

MAX_FILES = 100
MAX_FILE_SIZE = 40_000
MAX_CONTEXT = 150_000
MAX_RETRIES = 3

IGNORE_DIRS = {
    ".git",
    ".gradle",
    ".idea",
    "__pycache__",
    "node_modules",
    "build",
    "dist",
    ".venv",
    "venv"
}

HISTORY = []

SYSTEM = """
Ты Termux Code — AI coding agent внутри Android Termux.

Ты помогаешь пользователю программировать и работаешь
с файлами текущего проекта.

Ты можешь:
- анализировать код;
- создавать файлы;
- изменять существующие файлы;
- исправлять ошибки;
- объяснять код.

Если необходимо создать или изменить файл,
используй ТОЧНО такой формат:

<file path="main.py">
ПОЛНОЕ СОДЕРЖИМОЕ ФАЙЛА
</file>

Можно вернуть несколько файлов:

<file path="index.html">
...
</file>

<file path="style.css">
...
</file>

Правила:

1. Всегда возвращай ПОЛНОЕ новое содержимое изменяемого файла.
2. Не используй diff внутри <file>.
3. Не помещай <file> внутрь Markdown ``` блоков.
4. Не утверждай, что команда была выполнена, если она не выполнялась.
5. Не удаляй файлы без явной просьбы пользователя.
6. Работай только внутри текущего проекта.
"""


# =========================
# FILE SYSTEM
# =========================

def safe_path(path):
    try:
        path.resolve().relative_to(ROOT)
        return True
    except ValueError:
        return False


def get_files():
    files = []

    for path in ROOT.rglob("*"):

        if not path.is_file():
            continue

        relative = path.relative_to(ROOT)

        if any(part in IGNORE_DIRS for part in relative.parts):
            continue

        files.append(relative)

        if len(files) >= MAX_FILES:
            break

    return files


def read_file(relative):

    path = (ROOT / relative).resolve()

    if not safe_path(path):
        return "[BLOCKED]"

    try:

        if path.stat().st_size > MAX_FILE_SIZE:
            return "[FILE TOO LARGE]"

        return path.read_text(encoding="utf-8")

    except UnicodeDecodeError:
        return "[BINARY FILE]"

    except Exception as e:
        return f"[ERROR: {e}]"


def project_context():

    files = get_files()

    result = []

    result.append("PROJECT FILES:")

    for f in files:
        result.append(f"- {f}")

    result.append("\nFILE CONTENTS:")

    total = 0

    for f in files:

        content = read_file(f)

        block = f"""

--- FILE: {f} ---
{content}
--- END FILE ---

"""

        total += len(block)

        if total > MAX_CONTEXT:
            result.append("[CONTEXT LIMIT REACHED]")
            break

        result.append(block)

    return "\n".join(result)


# =========================
# GEMINI
# =========================

def api_url():
    return (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{MODEL}:generateContent?key={API_KEY}"
    )


def ask_gemini(prompt):

    context = project_context()

    conversation = []

    # Последние сообщения, чтобы контекст не рос бесконечно.
    for item in HISTORY[-8:]:
        conversation.append(
            f"{item['role'].upper()}: {item['text']}"
        )

    history_text = "\n\n".join(conversation)

    full_prompt = f"""
{context}

RECENT CONVERSATION:

{history_text}

USER REQUEST:

{prompt}
"""

    body = {

        "system_instruction": {
            "parts": [
                {
                    "text": SYSTEM
                }
            ]
        },

        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": full_prompt
                    }
                ]
            }
        ],

        "generationConfig": {
            "temperature": 0.2
        }
    }

    data = json.dumps(body).encode("utf-8")

    for attempt in range(1, MAX_RETRIES + 1):

        request = urllib.request.Request(
            api_url(),
            data=data,
            headers={
                "Content-Type": "application/json"
            },
            method="POST"
        )

        try:

            with urllib.request.urlopen(
                request,
                timeout=120
            ) as response:

                result = json.loads(
                    response.read().decode("utf-8")
                )

            candidates = result.get("candidates", [])

            if not candidates:
                return "❌ Gemini не вернул ответ."

            parts = candidates[0]["content"]["parts"]

            answer = "".join(
                p.get("text", "")
                for p in parts
            )

            return answer

        except urllib.error.HTTPError as e:

            error_text = e.read().decode(
                "utf-8",
                errors="replace"
            )

            # Перегрузка / rate limit
            if e.code in (429, 503):

                if attempt < MAX_RETRIES:

                    wait = attempt * 5

                    print(
                        f"⚠️ API временно недоступен ({e.code})."
                    )

                    print(
                        f"Повтор через {wait} сек..."
                    )

                    time.sleep(wait)

                    continue

            return (
                f"API ERROR {e.code}\n"
                f"{error_text}"
            )

        except Exception as e:

            if attempt < MAX_RETRIES:

                print(
                    f"⚠️ Ошибка соединения: {e}"
                )

                print("Повтор через 3 сек...")

                time.sleep(3)

                continue

            return f"❌ Ошибка: {e}"

    return "❌ Не удалось получить ответ."


# =========================
# AI FILE OUTPUT
# =========================

def parse_files(answer):

    pattern = re.compile(
        r'<file\s+path="([^"]+)">\s*(.*?)\s*</file>',
        re.DOTALL
    )

    return pattern.findall(answer)


def remove_file_blocks(answer):

    return re.sub(
        r'<file\s+path="[^"]+">\s*.*?\s*</file>',
        "",
        answer,
        flags=re.DOTALL
    ).strip()


def apply_files(files):

    if not files:
        return

    print("\n📁 Предлагаемые изменения:\n")

    valid = []

    for name, content in files:

        path = (ROOT / name).resolve()

        if not safe_path(path):

            print(
                f"🚫 Заблокирован путь: {name}"
            )

            continue

        valid.append(
            (name, path, content)
        )

        status = (
            "ИЗМЕНИТЬ"
            if path.exists()
            else "СОЗДАТЬ"
        )

        print(
            f" [{status}] {name}"
        )

    if not valid:
        return

    print()

    confirm = input(
        "Применить? [y/N]: "
    ).strip().lower()

    if confirm not in {
        "y",
        "yes",
        "да",
        "д"
    }:

        print("❌ Отменено.")
        return

    for name, path, content in valid:

        try:

            path.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            # Backup
            if path.exists():

                backup = Path(
                    str(path) + ".bak"
                )

                backup.write_bytes(
                    path.read_bytes()
                )

            path.write_text(
                content,
                encoding="utf-8"
            )

            print(
                f"✅ {name}"
            )

        except Exception as e:

            print(
                f"❌ {name}: {e}"
            )


# =========================
# COMMANDS
# =========================

def command_files():

    files = get_files()

    if not files:

        print("📂 Папка пустая.")
        return

    print()

    for f in files:

        print(
            " •",
            f
        )

    print()


def command_read(filename):

    path = (ROOT / filename).resolve()

    if not safe_path(path):

        print("🚫 Путь запрещён.")
        return

    if not path.exists():

        print("❌ Файл не найден.")
        return

    try:

        print()
        print(
            path.read_text(
                encoding="utf-8"
            )
        )
        print()

    except Exception as e:

        print(
            f"❌ {e}"
        )


def command_run(filename):

    path = (ROOT / filename).resolve()

    if not safe_path(path):

        print("🚫 Путь запрещён.")
        return

    if not path.exists():

        print("❌ Файл не найден.")
        return

    if path.suffix != ".py":

        print(
            "⚠️ /run сейчас запускает только .py"
        )
        return

    print(
        f"\n▶ Запуск {filename}\n"
    )

    try:

        subprocess.run(
            ["python", str(path)],
            cwd=ROOT
        )

    except KeyboardInterrupt:

        print(
            "\n⏹ Остановлено."
        )

    except Exception as e:

        print(
            f"❌ {e}"
        )


def help_menu():

    print("""
TERMUX CODE COMMANDS

/files
    показать файлы

/read main.py
    прочитать файл

/run main.py
    запустить Python-файл

/clear
    очистить историю AI

/help
    показать команды

/exit
    выйти
""")


# =========================
# MAIN
# =========================

def main():

    print("""
╔════════════════════════════════╗
║       TERMUX CODE v2           ║
║       Gemini AI Agent          ║
╚════════════════════════════════╝
""")

    print(
        "📂 Проект:",
        ROOT
    )

    print(
        "🤖 Модель:",
        MODEL
    )

    print()

    print(
        "Введите /help для команд.\n"
    )

    while True:

        try:

            prompt = input(
                "Termux Code > "
            ).strip()

            if not prompt:
                continue

            # EXIT

            if prompt in {
                "/exit",
                "exit",
                "quit"
            }:

                print("👋 Пока!")
                break

            # HELP

            if prompt == "/help":

                help_menu()
                continue

            # FILES

            if prompt == "/files":

                command_files()
                continue

            # READ

            if prompt.startswith("/read "):

                filename = (
                    prompt[6:].strip()
                )

                command_read(
                    filename
                )

                continue

            # RUN

            if prompt.startswith("/run "):

                filename = (
                    prompt[5:].strip()
                )

                command_run(
                    filename
                )

                continue

            # CLEAR HISTORY

            if prompt == "/clear":

                HISTORY.clear()

                print(
                    "🧹 История очищена."
                )

                continue

            # AI

            print(
                "\n🤖 Gemini думает...\n"
            )

            answer = ask_gemini(
                prompt
            )

            files = parse_files(
                answer
            )

            text = remove_file_blocks(
                answer
            )

            if text:

                print(text)
                print()

            # История

            HISTORY.append(
                {
                    "role": "user",
                    "text": prompt
                }
            )

            HISTORY.append(
                {
                    "role": "assistant",
                    "text": text[:5000]
                }
            )

            # Файлы

            apply_files(
                files
            )

            print()

        except KeyboardInterrupt:

            print(
                "\n👋 Выход."
            )

            break


if __name__ == "__main__":
    main()
