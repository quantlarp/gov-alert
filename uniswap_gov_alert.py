#!/usr/bin/env python3
"""
Uniswap Governance → Telegram alert bot (local test version).

- Watches the Uniswap "Proposal Discussion / RFC" category:
  https://gov.uniswap.org/c/proposal-discussion/5

- Env vars:
    TELEGRAM_BOT_TOKEN  - your bot token from BotFather
    TELEGRAM_CHAT_ID    - your chat id (the chat with the bot)
    FORCE_LATEST        - "true"/"1"/"yes" to send a test alert for latest topic

Normal mode:
    - Tracks last_seen topic ID in uniswap_last_seen.json
    - Sends alerts only for topics with id > last_seen

Test mode (FORCE_LATEST=true):
    - Ignores state and sends a [TEST] alert for the latest topic
    - Does NOT modify the state file
"""

import os
import json
import requests
from typing import Dict, Any, List

# ---- Config ----

UNISWAP_FORUM_NAME = "Uniswap Proposal Discussion"
UNISWAP_CATEGORY_JSON = "https://gov.uniswap.org/c/proposal-discussion/5.json"
UNISWAP_BASE_URL = "https://gov.uniswap.org"
STATE_FILE = "uniswap_last_seen.json"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
FORCE_LATEST = os.getenv("FORCE_LATEST", "").lower() in ("1", "true", "yes")


# ---- Helpers ----

def send_telegram(text: str) -> None:
    """Send a Telegram message using the bot token & chat ID from env vars."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        # no parse_mode → plain text, less likely to error
    }
    r = requests.post(url, json=payload, timeout=15)
    print("Telegram response:", r.status_code, r.text)  # debug line
    r.raise_for_status()



def fetch_uniswap_topics() -> List[Dict[str, Any]]:
    """Fetch topics from the Uniswap Proposal Discussion category."""
    r = requests.get(UNISWAP_CATEGORY_JSON, timeout=15)
    r.raise_for_status()
    data = r.json()
    topics = data.get("topic_list", {}).get("topics", [])
    # ensure newest-first
    topics.sort(key=lambda t: t["id"], reverse=True)
    return topics


def load_last_seen(path: str) -> int:
    """Load the last seen topic id from a JSON file, or 0 if not present."""
    if not os.path.exists(path):
        return 0
    with open(path, "r") as f:
        obj = json.load(f)
    return int(obj.get("last_topic_id", 0))


def save_last_seen(path: str, topic_id: int) -> None:
    """Save the last seen topic id to a JSON file."""
    with open(path, "w") as f:
        json.dump({"last_topic_id": int(topic_id)}, f)


# ---- Core logic ----

def run_force_latest(topics: List[Dict[str, Any]]) -> None:
    """
    Test mode: ignore state and send an alert for the newest topic.

    Does NOT update the state file.
    """
    if not topics:
        print("No topics found on Uniswap forum (force_latest).")
        return

    latest = topics[0]
    title = latest["title"]
    slug = latest["slug"]
    topic_id = latest["id"]
    url = f"{UNISWAP_BASE_URL}/t/{slug}/{topic_id}"

    msg = (
        f"*[TEST]* Latest topic on {UNISWAP_FORUM_NAME}*\n"
        f"{title}\n"
        f"{url}"
    )
    print(f"Sending test Telegram alert for topic ID {topic_id}")
    send_telegram(msg)


def run_normal(topics: List[Dict[str, Any]], state_path: str) -> None:
    """Normal mode: track new topics since last_seen and alert on them."""
    if not topics:
        print("No topics found on Uniswap forum.")
        return

    if not os.path.exists(state_path):
        # First run: initialize last_seen to the current max id to avoid spam
        max_id = max(t["id"] for t in topics)
        save_last_seen(state_path, max_id)
        print(f"Initialized last_seen to {max_id}, no alerts sent on first run.")
        return

    last_seen = load_last_seen(state_path)
    new_topics = [t for t in topics if t["id"] > last_seen]

    if not new_topics:
        print(f"No new topics since last_seen={last_seen}.")
        return

    # oldest→newest for clean chronological alerts
    new_topics_sorted = sorted(new_topics, key=lambda t: t["id"])

    for t in new_topics_sorted:
        title = t["title"]
        slug = t["slug"]
        topic_id = t["id"]
        url = f"{UNISWAP_BASE_URL}/t/{slug}/{topic_id}"

        msg = (
            f"*New Uniswap governance thread*\n"
            f"{title}\n"
            f"{url}"
        )
        print(f"Sending Telegram alert for new topic ID {topic_id}")
        send_telegram(msg)
        last_seen = topic_id

    save_last_seen(state_path, last_seen)
    print(f"Updated last_seen to {last_seen}.")


def main() -> None:
    topics = fetch_uniswap_topics()

    if FORCE_LATEST:
        print("Running in FORCE_LATEST (test) mode.")
        run_force_latest(topics)
    else:
        print("Running in normal mode.")
        run_normal(topics, STATE_FILE)


if __name__ == "__main__":
    main()
