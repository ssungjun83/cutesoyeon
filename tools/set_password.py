from __future__ import annotations

from getpass import getpass
from pathlib import Path

from werkzeug.security import generate_password_hash


def main() -> int:
    base = Path(__file__).resolve().parent.parent
    env_path = base / ".env"

    pw1 = getpass("웹 비밀번호를 입력하세요: ")
    pw2 = getpass("한 번 더 입력하세요: ")
    if not pw1 or pw1 != pw2:
        print("비밀번호가 비어있거나 서로 다릅니다.")
        return 1

    env_path.write_text(
        f"CHAT_APP_PASSWORD_HASH=\"{generate_password_hash(pw1)}\"\n"
        "CHAT_APP_HOST=127.0.0.1\n"
        "CHAT_APP_PORT=8000\n",
        encoding="utf-8",
    )
    print(f"완료: {env_path} 생성")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
