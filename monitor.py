#!/usr/bin/env python3
"""
Carnegie Hall Event Page Monitor
Watches the Jacob Collier event page for ANY change and emails on change.
"""

import hashlib
import json
import os
import re
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────

URL        = "https://www.carnegiehall.org/calendar/2026/09/30/jacob-collier-0800pm"
STATE_FILE = "state.json"

EMAIL_SENDER    = os.environ["EMAIL_SENDER"]
EMAIL_PASSWORD  = os.environ["EMAIL_PASSWORD"]
EMAIL_RECIPIENT = os.environ["EMAIL_RECIPIENT"]
RECIPIENT_LIST  = [e.strip() for e in EMAIL_RECIPIENT.split(",") if e.strip()]

# ─────────────────────────────────────────────


def fetch_page(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.carnegiehall.org/calendar",
    }
    req = Request(url, headers=headers)
    with urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="replace")


def clean_content(html: str) -> str:
    """
    Strip out the noisy parts that change on every load (tokens, timestamps,
    nonces, session IDs) so we only alert on meaningful changes.
    """
    text = html
    # Remove script/style blocks
    text = re.sub(r"<script.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Remove common volatile patterns
    text = re.sub(r'nonce="[^"]*"', "", text)
    text = re.sub(r'csrf[-_]?token[^"]*"[^"]*"', "", text, flags=re.IGNORECASE)
    text = re.sub(r'data-[a-z]*id="[^"]*"', "", text, flags=re.IGNORECASE)
    text = re.sub(r'\b[0-9a-f]{32,}\b', "", text)          # long hex tokens
    text = re.sub(r'\d{10,13}', "", text)                  # unix timestamps
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def send_email(old_hash: str, new_hash: str) -> None:
    subject = "🔔 Carnegie Hall page changed — Jacob Collier 9/30"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    body = f"""
A change was detected on the Carnegie Hall event page.

Event:    Jacob Collier — Sept 30, 2026, 8:00 PM
Detected: {timestamp}
Page:     {URL}

Old hash: {old_hash}
New hash: {new_hash}

➡ Check the page now: {URL}
"""
    msg = MIMEMultipart()
    msg["From"]    = EMAIL_SENDER
    msg["To"]      = ", ".join(RECIPIENT_LIST)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, RECIPIENT_LIST, msg.as_string())

    print(f"  ✉  Alert sent to {RECIPIENT_LIST}")


def main() -> None:
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking Carnegie Hall page...")

    try:
        html = fetch_page(URL)
    except HTTPError as e:
        print(f"  ✗  HTTP {e.code}: site may be blocking automated access.")
        return
    except URLError as e:
        print(f"  ✗  Could not reach page: {e}")
        return

    print(f"  Fetched {len(html)} bytes")
    cleaned = clean_content(html)
    current_hash = hashlib.md5(cleaned.encode("utf-8")).hexdigest()
    print(f"  Content hash: {current_hash}  (cleaned length: {len(cleaned)} chars)")

    state = load_state()
    previous_hash = state.get("hash")

    if previous_hash is None:
        print("  ✓  First run — baseline saved. No alert sent.")
    elif current_hash == previous_hash:
        print("  ✓  No change detected.")
    else:
        print(f"  ⚠  Change detected! {previous_hash} → {current_hash}")
        try:
            send_email(previous_hash, current_hash)
        except Exception as e:
            print(f"  ✗  Email failed: {e}")

    state["hash"] = current_hash
    state["last_checked"] = datetime.now().isoformat()
    save_state(state)


if __name__ == "__main__":
    main()
