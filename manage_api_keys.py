"""CLI-утилита для управления API-ключами.

Использование:
  python manage_api_keys.py create <name>   — создать новый ключ
  python manage_api_keys.py revoke <name>   — отозвать ключ по имени
  python manage_api_keys.py list            — показать все ключи

Ключ генерируется как 64-символьная hex-строка (secrets.token_hex(32)).
В Firestore хранится только SHA-256 хэш — сырой ключ нигде не сохраняется,
поэтому его нужно скопировать сразу после создания.
"""
import asyncio
import hashlib
import secrets
import sys
from datetime import datetime

from bot.api.task_repo import ApiTaskRepo
from bot.core.config import get_settings


def _hash(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def cmd_create(name: str) -> None:
    settings = get_settings()
    repo = ApiTaskRepo(settings)

    raw_key = secrets.token_hex(32)
    key_id = await repo.create_key(name, _hash(raw_key))

    print()
    print("✅ Ключ успешно создан!")
    print(f"   Имя    : {name}")
    print(f"   ID     : {key_id}")
    print(f"   Ключ   : {raw_key}")
    print()
    print("⚠️  Сохрани ключ прямо сейчас — повторно он показан не будет!")
    print()
    print("Заголовок для запросов:")
    print(f"   Authorization: Bearer {raw_key}")
    print()


async def cmd_revoke(name: str) -> None:
    settings = get_settings()
    repo = ApiTaskRepo(settings)

    found = await repo.revoke_key(name)
    if found:
        print(f"✅ Ключ '{name}' отозван")
    else:
        print(f"❌ Ключ '{name}' не найден или уже отозван")


async def cmd_list() -> None:
    settings = get_settings()
    repo = ApiTaskRepo(settings)

    keys = await repo.list_keys()
    if not keys:
        print("Ключей нет")
        return

    header = f"{'ID':<38}  {'Имя':<20}  {'Активен':<8}  Создан"
    print()
    print(header)
    print("-" * len(header))
    for k in sorted(keys, key=lambda x: x.get("created_at") or datetime.min):
        created_at = k.get("created_at")
        created = created_at.strftime("%Y-%m-%d %H:%M") if isinstance(created_at, datetime) else "—"
        flag = "✅" if k.get("is_active") else "❌"
        print(f"{k['key_id']:<38}  {k['name']:<20}  {flag:<8}  {created}")
    print()


def _usage() -> None:
    print(__doc__)


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        _usage()
        sys.exit(0)

    cmd = args[0]

    if cmd == "create":
        if len(args) < 2:
            print("Ошибка: укажи имя ключа.\n  python manage_api_keys.py create <name>")
            sys.exit(1)
        asyncio.run(cmd_create(args[1]))

    elif cmd == "revoke":
        if len(args) < 2:
            print("Ошибка: укажи имя ключа.\n  python manage_api_keys.py revoke <name>")
            sys.exit(1)
        asyncio.run(cmd_revoke(args[1]))

    elif cmd == "list":
        asyncio.run(cmd_list())

    else:
        print(f"Неизвестная команда: {cmd}")
        _usage()
        sys.exit(1)
