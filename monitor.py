#!/usr/bin/env python3
"""Feed-based alert monitor: fetch RSS/Atom feeds, filter by keywords,
skip already-seen items, and notify via Slack / Telegram / stdout."""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

CONFIG = os.environ.get("MONITOR_CONFIG", "config.json")
STATE = os.environ.get("MONITOR_STATE", "seen.json")
ATOM = "{http://www.w3.org/2005/Atom}"


def http(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {"User-Agent": "alert-monitor/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def parse_feed(xml_bytes):
    root = ET.fromstring(xml_bytes)
    items = []
    for it in root.iter("item"):  # RSS
        items.append({
            "id": (it.findtext("guid") or it.findtext("link") or "").strip(),
            "title": (it.findtext("title") or "").strip(),
            "link": (it.findtext("link") or "").strip(),
            "summary": re.sub(r"<[^>]+>", " ", it.findtext("description") or "").strip(),
        })
    for en in root.iter(ATOM + "entry"):  # Atom
        link = en.find(ATOM + "link")
        href = link.get("href", "") if link is not None else ""
        items.append({
            "id": (en.findtext(ATOM + "id") or href).strip(),
            "title": (en.findtext(ATOM + "title") or "").strip(),
            "link": href,
            "summary": re.sub(r"<[^>]+>", " ", en.findtext(ATOM + "summary") or "").strip(),
        })
    return items


def matches(item, watch):
    text = f"{item['title']} {item['summary']}".lower()
    inc = [k.lower() for k in watch.get("include", [])]
    exc = [k.lower() for k in watch.get("exclude", [])]
    if inc and not any(k in text for k in inc):
        return False
    return not any(k in text for k in exc)


def notify(msg):
    sent = False
    if os.environ.get("SLACK_WEBHOOK_URL"):
        http(os.environ["SLACK_WEBHOOK_URL"], json.dumps({"text": msg}).encode(),
             {"Content-Type": "application/json"})
        sent = True
    if os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"):
        http(f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage",
             urllib.parse.urlencode({"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": msg}).encode())
        sent = True
    if not sent:
        print(msg)


def main():
    with open(CONFIG) as f:
        watches = json.load(f)["watches"]
    seen = set(json.load(open(STATE))) if os.path.exists(STATE) else set()
    first_run = not os.path.exists(STATE)
    new = []
    for w in watches:
        try:
            items = parse_feed(http(w["url"]))
        except Exception as e:  # one bad feed shouldn't stop the rest
            print(f"[warn] {w['name']}: {e}", file=sys.stderr)
            continue
        for it in items:
            key = f"{w['name']}|{it['id'] or it['link']}"
            if key in seen:
                continue
            seen.add(key)
            if matches(it, w):
                new.append((w["name"], it))
    # On first run just record the backlog, so you aren't flooded.
    if not first_run:
        for name, it in new:
            notify(f"[{name}] {it['title']}\n{it['link']}")
    json.dump(sorted(seen), open(STATE, "w"), indent=0)
    print(f"{len(new)} matching new item(s){' (first run, suppressed)' if first_run else ''}")


if __name__ == "__main__":
    main()
