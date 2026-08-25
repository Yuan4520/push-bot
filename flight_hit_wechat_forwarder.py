import json
import os
import time
from html import escape
from pathlib import Path

import requests
from dotenv import load_dotenv


BASE_URL = "http://127.0.0.1:8000"
STATE_PATH = Path("data/flight_forwarder_state.json")


def load_state():
    if not STATE_PATH.exists():
        return {"last_alert_id": 0}
    with STATE_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with STATE_PATH.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def send_serverchan(title, content, sendkey):
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    response = requests.post(url, data={"title": title, "desp": content}, timeout=20)
    response.raise_for_status()
    return response.text


def send_pushplus(title, content, token):
    response = requests.post(
        "https://www.pushplus.plus/send",
        json={
            "token": token,
            "title": title,
            "content": escape(content).replace("\n", "<br>"),
            "template": "html",
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.text


def send_wechat(title, content):
    serverchan_sendkey = os.getenv("SERVERCHAN_SENDKEY", "").strip()
    pushplus_token = os.getenv("PUSHPLUS_TOKEN", "").strip()
    if serverchan_sendkey:
        return send_serverchan(title, content, serverchan_sendkey)
    if pushplus_token:
        return send_pushplus(title, content, pushplus_token)
    raise RuntimeError("请在 .env 中填写 SERVERCHAN_SENDKEY 或 PUSHPLUS_TOKEN")


def format_alert(alert):
    title = f"机票低价命中：{alert['origin_city']} -> {alert['destination_city']}"
    content = (
        f"航线：{alert['origin_city']} -> {alert['destination_city']}\n"
        f"日期：{alert['departure_date']}\n"
        f"当前最低价：{alert['lowest_price']} 元\n"
        f"目标价：{alert['target_price']} 元\n"
        f"命中时间：{alert['hit_at']}\n"
        f"本地详情：{alert.get('url', BASE_URL)}"
    )
    return title, content


def poll_once():
    state = load_state()
    last_alert_id = int(state.get("last_alert_id", 0))
    response = requests.get(f"{BASE_URL}/api/monitor-alerts", params={"after_id": last_alert_id}, timeout=20)
    response.raise_for_status()
    payload = response.json()
    alerts = payload.get("alerts", payload) if isinstance(payload, dict) else payload
    for alert in alerts:
        title, content = format_alert(alert)
        send_wechat(title, content)
        last_alert_id = max(last_alert_id, int(alert["hit_id"]))
    state["last_alert_id"] = last_alert_id
    save_state(state)
    return len(alerts)


def main():
    load_dotenv()
    interval_seconds = int(os.getenv("FLIGHT_FORWARDER_INTERVAL_SECONDS", "300"))
    while True:
        try:
            count = poll_once()
            if count:
                print(f"forwarded={count}", flush=True)
        except Exception as exc:
            print(f"forwarder_error={exc}", flush=True)
        time.sleep(interval_seconds)


if __name__ == "__main__":
    main()
