from __future__ import annotations

import os
from pathlib import Path
import secrets
from datetime import datetime

from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash

from kakao_parser import parse_kakao_talk_txt
from storage import fetch_messages, import_messages


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("CHAT_APP_DATA_DIR", "")).expanduser().resolve() if os.getenv("CHAT_APP_DATA_DIR") else (BASE_DIR / "data")
DB_PATH = DATA_DIR / "chat.db"
SECRET_KEY_PATH = DATA_DIR / "secret_key.txt"


def _ensure_secret_key() -> str:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if SECRET_KEY_PATH.exists():
        return SECRET_KEY_PATH.read_text(encoding="utf-8").strip()
    key = secrets.token_hex(32)
    SECRET_KEY_PATH.write_text(key, encoding="utf-8")
    return key


def _decode_uploaded_bytes(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _require_login() -> None:
    if not session.get("logged_in"):
        abort(401)


def create_app() -> Flask:
    load_dotenv(BASE_DIR / ".env", interpolate=False, encoding="utf-8-sig")

    password_hash = os.getenv("CHAT_APP_PASSWORD_HASH", "").strip().strip('"').strip("'")
    if not password_hash:
        raise RuntimeError(
            "CHAT_APP_PASSWORD_HASH가 필요합니다. tools/set_password.py를 실행해 .env를 만든 뒤 다시 실행하세요."
        )

    app = Flask(__name__)
    app.secret_key = os.getenv("CHAT_APP_SECRET_KEY", "").strip() or _ensure_secret_key()
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )

    app.config["CHAT_ME_NAME"] = os.getenv("CHAT_APP_ME", "").strip()
    app.config["CHAT_PASSWORD_HASH"] = password_hash

    @app.errorhandler(401)
    def _unauthorized(_err):
        return redirect(url_for("login", next=request.path))

    @app.get("/login")
    def login():
        return render_template("login.html")

    @app.post("/login")
    def login_post():
        password = request.form.get("password", "")
        if not check_password_hash(app.config["CHAT_PASSWORD_HASH"], password):
            flash("비밀번호가 틀렸습니다.", "error")
            return redirect(url_for("login"))
        session["logged_in"] = True
        session.permanent = True
        return redirect(url_for("index"))

    @app.get("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.get("/")
    def index():
        _require_login()
        before = request.args.get("before")
        view = request.args.get("view", "chat").strip().lower()
        if view not in ("chat", "txt"):
            view = "chat"

        messages = fetch_messages(DB_PATH, limit=300, before_dt=before)
        for m in messages:
            dt = datetime.fromisoformat(m["dt"])
            m["date_key"] = dt.strftime("%Y-%m-%d")
            weekday_ko = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"][dt.weekday()]
            m["date_ko"] = f"{dt.year}년 {dt.month}월 {dt.day}일 {weekday_ko}"
            ampm = "오전" if dt.hour < 12 else "오후"
            h12 = dt.hour % 12
            if h12 == 0:
                h12 = 12
            m["time_ko"] = f"{ampm} {h12}:{dt.minute:02d}"

        next_before = messages[0]["dt"] if messages else None
        template = "chat_txt.html" if view == "txt" else "chat.html"
        raw_text = None
        if view == "txt":
            parts: list[str] = []
            last_day: str | None = None
            for m in messages:
                if m["date_key"] != last_day:
                    parts.append(f"--------------- {m['date_ko']} ---------------")
                    last_day = m["date_key"]
                parts.append(f"[{m['sender']}] [{m['time_ko']}] {m['text']}")
            raw_text = "\n".join(parts)
        return render_template(
            template,
            messages=messages,
            me_name=app.config["CHAT_ME_NAME"],
            next_before=next_before,
            view=view,
            raw_text=raw_text,
        )

    @app.get("/admin/import")
    def admin_import():
        _require_login()
        return render_template("import.html")

    @app.post("/admin/import")
    def admin_import_post():
        _require_login()

        source_label = ""
        text = ""

        if "file" in request.files and request.files["file"].filename:
            up = request.files["file"]
            source_label = up.filename
            text = _decode_uploaded_bytes(up.read())
        else:
            text = request.form.get("text", "")
            source_label = "pasted"

        if not text.strip():
            flash("가져올 내용이 비어있습니다.", "error")
            return redirect(url_for("admin_import"))

        msgs = parse_kakao_talk_txt(text)
        if not msgs:
            flash("메시지를 찾지 못했습니다. (파일 형식을 확인하세요)", "error")
            return redirect(url_for("admin_import"))

        result = import_messages(DB_PATH, msgs, source=source_label)
        flash(
            f"가져오기 완료: {result['inserted']}개 추가, {result['skipped']}개 중복 제외 (총 {result['total']}개 파싱)",
            "ok",
        )
        return redirect(url_for("index"))

    return app


if __name__ == "__main__":
    app = create_app()
    host = os.getenv("CHAT_APP_HOST", "127.0.0.1")
    port = int(os.getenv("CHAT_APP_PORT", "8000"))
    app.run(host=host, port=port, debug=False)
