from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import re


@dataclass(frozen=True)
class KakaoMessage:
    dt: datetime
    sender: str
    text: str


_DATE_SEPARATOR_RE = re.compile(
    r"^-{5,}\s*(?P<y>\d{4})년\s*(?P<m>\d{1,2})월\s*(?P<d>\d{1,2})일.*?-{5,}\s*$"
)

_MESSAGE_RE = re.compile(
    r"^\[(?P<sender>.+?)\]\s+\[(?P<ampm>오전|오후)\s+(?P<h>\d{1,2}):(?P<min>\d{2})\]\s(?P<body>.*)$"
)


def _normalize_text_for_dedup(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def normalize_text_for_dedup(text: str) -> str:
    return _normalize_text_for_dedup(text)


def _parse_ampm_time(ampm: str, hour: int, minute: int) -> tuple[int, int]:
    if ampm not in ("오전", "오후"):
        raise ValueError(f"Unsupported AM/PM marker: {ampm}")
    if ampm == "오전" and hour == 12:
        hour = 0
    elif ampm == "오후" and hour != 12:
        hour += 12
    return hour, minute


def parse_kakao_talk_txt(text: str) -> list[KakaoMessage]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    current_date: date | None = None
    messages: list[KakaoMessage] = []

    for line in lines:
        date_match = _DATE_SEPARATOR_RE.match(line)
        if date_match:
            current_date = date(
                int(date_match.group("y")),
                int(date_match.group("m")),
                int(date_match.group("d")),
            )
            continue

        msg_match = _MESSAGE_RE.match(line)
        if msg_match and current_date is not None:
            hour_12 = int(msg_match.group("h"))
            minute = int(msg_match.group("min"))
            hour_24, minute = _parse_ampm_time(msg_match.group("ampm"), hour_12, minute)
            dt = datetime(
                current_date.year,
                current_date.month,
                current_date.day,
                hour_24,
                minute,
                0,
            )
            messages.append(
                KakaoMessage(
                    dt=dt,
                    sender=msg_match.group("sender").strip(),
                    text=msg_match.group("body"),
                )
            )
            continue

        if messages:
            messages[-1] = KakaoMessage(
                dt=messages[-1].dt,
                sender=messages[-1].sender,
                text=f"{messages[-1].text}\n{line}",
            )

    return messages

