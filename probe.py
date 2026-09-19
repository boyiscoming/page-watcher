"""One-shot probe: can GitHub's runner fetch the page, and what markers does it contain?
Prints only flags/snippets (never the URL). Saves full HTML to page.html for the artifact.
"""
import os
import re
import sys
import urllib.error
import urllib.request

URL = os.environ["PAGE_URL"]
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Safari/605.1.15")

req = urllib.request.Request(URL, headers={
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-AU,en;q=0.9",
})

try:
    with urllib.request.urlopen(req, timeout=30) as r:
        status, body = r.status, r.read().decode("utf-8", "replace")
        ctype = r.headers.get("Content-Type")
except urllib.error.HTTPError as e:
    status, body, ctype = e.code, e.read().decode("utf-8", "replace"), e.headers.get("Content-Type")
except Exception as e:  # network-level failure
    print(f"REQUEST FAILED: {type(e).__name__}: {e}")
    sys.exit(1)

open("page.html", "w", encoding="utf-8").write(body)
low = body.lower()

print(f"status={status} content-type={ctype} length={len(body)}")
print("anchor 'wadjemup'      :", "wadjemup" in low)
print("has 'booked out'       :", "booked out" in low or "booked_out" in low or "bookedout" in low)
print("has 'create booking'   :", "create booking" in low)
print("block hints            :", [k for k in
      ("captcha", "access denied", "incapsula", "akamai", "cloudflare", "unusual traffic", "bot")
      if k in low])


def snippet(word, radius=250):
    m = re.search(re.escape(word), low)
    return body[max(0, m.start() - radius): m.end() + radius] if m else None


for w in ("booked", "create booking"):
    s = snippet(w)
    print(f"\n--- snippet around '{w}' ---")
    print(s if s else "(not found)")
