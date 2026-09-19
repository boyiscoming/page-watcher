"""Booking watcher: notify via Telegram when the 'BOOKED OUT' banner disappears.
Notification only - never books or pays anything.
Never print the URL, token, or HTML (repo logs are public).
"""
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

URL = os.environ["PAGE_URL"]
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT = os.environ["TELEGRAM_CHAT_ID"]
TEST_ONLY = os.environ.get("TEST_ONLY", "").lower() == "true"

AWST = timezone(timedelta(hours=8))                    # Perth
STOP_AT = datetime(2026, 10, 3, 8, 0, tzinfo=AWST)     # stop watching at event morning
RUN_SECONDS = 345 * 60                                 # stay under the 6h job limit
INTERVAL = 60                                          # base seconds between checks
MAX_AVAILABLE_ALERTS = 12

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Safari/605.1.15")


def tg(text, silent=False):
    data = urllib.parse.urlencode({
        "chat_id": CHAT,
        "text": text,
        "disable_notification": "true" if silent else "false",
        "disable_web_page_preview": "true",
    }).encode()
    try:
        urllib.request.urlopen(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage", data=data, timeout=20
        ).read()
        return True
    except Exception as e:
        print("telegram send failed:", type(e).__name__, flush=True)  # no details: may contain token
        return False


def fetch():
    req = urllib.request.Request(URL, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-AU,en;q=0.9",
    })
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return 0, ""


def classify(status, html):
    low = html.lower()
    # Must look like the real booking page, otherwise we can't trust the result.
    if status != 200 or "wadjemup" not in low or "uds_create_booking" not in low:
        return "UNKNOWN"
    booked_out = (
        re.search(r'<div[^>]*class=["\']?fullyBooked', html, re.I)
        or re.search(r">\s*BOOKED\s*OUT\s*<", html, re.I)
    )
    return "BOOKED_OUT" if booked_out else "AVAILABLE"


def main():
    if TEST_ONLY:
        ok = tg("✅ 테스트 메시지: Telegram 알림 연결 성공")
        print("test message sent" if ok else "test message FAILED")
        sys.exit(0 if ok else 1)

    if datetime.now(AWST) >= STOP_AT:
        print("Past stop time, exiting.")
        return

    tg("👀 감시 시작/재개 (이 알림은 무음이에요)", silent=True)
    start = time.time()
    unknown_streak = 0
    available_count = 0
    sent_available_alerts = 0

    while time.time() - start < RUN_SECONDS and datetime.now(AWST) < STOP_AT:
        status, html = fetch()
        state = classify(status, html)
        print(datetime.now(AWST).strftime("%m-%d %H:%M:%S"), state, status, len(html), flush=True)

        if state == "AVAILABLE":
            unknown_streak = 0
            if available_count % 5 == 0 and sent_available_alerts < MAX_AVAILABLE_ALERTS:
                tg("🚨 예약 가능할 수 있어요! 'BOOKED OUT' 표시가 사라졌습니다.\n"
                   f"바로 열어서 확인하세요:\n{URL}")
                sent_available_alerts += 1
            available_count += 1
        elif state == "UNKNOWN":
            available_count = 0
            unknown_streak += 1
            if unknown_streak in (5, 60):
                tg("⚠️ 페이지를 정상적으로 읽지 못하고 있어요 (차단/주소 만료/페이지 변경 가능). "
                   "직접 확인해 주세요.")
        else:  # BOOKED_OUT
            unknown_streak = 0
            available_count = 0
            sent_available_alerts = 0

        time.sleep(INTERVAL + random.uniform(0, 15))


if __name__ == "__main__":
    main()
