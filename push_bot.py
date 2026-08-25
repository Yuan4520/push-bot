import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime
from html import escape
from pathlib import Path

import feedparser
import requests
from dotenv import load_dotenv


CITY_CODES = {
    "广州": "CAN",
    "深圳": "SZX",
    "珠海": "ZUH",
    "兰州": "LHW",
    "西宁": "XNN",
}
CITY_NAMES = {value: key for key, value in CITY_CODES.items()}
JIPIAO_DB_PATH = Path("references/JiPiao-master/data/prices.db")


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_weather(city, display_name=None):
    url = f"https://wttr.in/{city}?format=j1"
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 personal-wechat-push-bot"},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        current = data["current_condition"][0]
        today = data["weather"][0]
        location = display_name or city
        return (
            f"城市：{location}\n"
            f"当前：{current['temp_C']}°C，体感 {current['FeelsLikeC']}°C，"
            f"{current['weatherDesc'][0]['value']}\n"
            f"今日：{today['mintempC']}°C - {today['maxtempC']}°C\n"
            f"湿度：{current['humidity']}%，风速：{current['windspeedKmph']} km/h"
        )
    except (requests.RequestException, KeyError, IndexError, ValueError) as exc:
        return f"天气源暂时不可用：{exc}"


def get_weather_report(weather_config):
    cities = weather_config.get("cities")
    if not cities:
        city = weather_config.get("city", "Wuhan")
        return get_weather(city)

    reports = []
    for city_config in cities:
        if isinstance(city_config, str):
            reports.append(get_weather(city_config))
            continue
        query = city_config.get("query") or city_config.get("name")
        name = city_config.get("name") or query
        if query:
            reports.append(get_weather(query, display_name=name))
    return "\n\n".join(reports) if reports else "未配置天气地点。"


def get_news(news_config):
    keywords = [k.lower() for k in news_config.get("keywords", []) if k.strip()]
    max_items = int(news_config.get("max_items", 8))
    items = []
    failed_sources = 0

    if news_config.get("daily_60s_enabled", True):
        daily_news = get_daily_60s_news(max_items=max_items)
        if daily_news:
            return daily_news

    for feed_url in news_config.get("feeds", []):
        try:
            response = requests.get(
                feed_url,
                headers={"User-Agent": "Mozilla/5.0 personal-wechat-push-bot"},
                timeout=20,
            )
            response.raise_for_status()
            parsed = feedparser.parse(response.content)
        except requests.RequestException:
            failed_sources += 1
            continue
        for entry in parsed.entries:
            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()
            summary = getattr(entry, "summary", "").strip()
            haystack = f"{title} {summary}".lower()
            if keywords and not any(keyword in haystack for keyword in keywords):
                continue
            if title and link:
                items.append((title, link))
            if len(items) >= max_items:
                break
        if len(items) >= max_items:
            break

    if not items:
        if failed_sources:
            return f"没有匹配到新闻；有 {failed_sources} 个新闻源请求失败。"
        return "没有匹配到新闻。"

    lines = []
    for index, (title, link) in enumerate(items, start=1):
        lines.append(f"{index}. {title}\n{link}")
    return "\n\n".join(lines)


def get_daily_60s_news(max_items=12):
    endpoints = [
        "https://60s.viki.moe/v2/60s",
        "https://60s.viki.moe/v2/60s?encoding=json",
    ]
    for url in endpoints:
        try:
            response = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 personal-wechat-push-bot"},
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data", payload)
            news_items = data.get("news") or data.get("data") or []
            if not news_items:
                continue
            date = data.get("date", "")
            tip = data.get("tip", "")
            lines = []
            if date:
                lines.append(f"日期：{date}")
                lines.append("")
            for index, item in enumerate(news_items[:max_items], start=1):
                lines.append(f"{index}. {item}")
            if tip:
                lines.append("")
                lines.append(f"每日一句：{tip}")
            return "\n".join(lines)
        except (requests.RequestException, ValueError, AttributeError):
            continue
    return ""


def get_flights_note(flights_config):
    routes = flights_config.get("routes", [])
    if not routes:
        return "未配置机票路线。"

    latest_prices = load_latest_flight_prices(JIPIAO_DB_PATH, flights_config)
    if latest_prices:
        return get_flight_price_report(routes, latest_prices)

    lines = [
        "还没有查价结果。可先运行 JiPiao 飞猪监控：",
        "PowerShell: .\\start_jipiao_fliggy.ps1",
        "",
        "当前关注：",
    ]
    for route in routes:
        lines.append(
            f"- {route.get('from', '出发地')} -> {route.get('to', '目的地')}，"
            f"日期：{route.get('date', '未填')}，目标价：{route.get('target_price', '未填')} 元"
        )
    return "\n".join(lines)


def load_latest_flight_prices(db_path, flights_config=None):
    if not db_path.exists():
        return {}
    flights_config = flights_config or {}

    query = """
        SELECT fp.*
        FROM flight_prices fp
        JOIN (
            SELECT platform, from_city, to_city, depart_date, MAX(fetched_at) AS fetched_at
            FROM flight_prices
            GROUP BY platform, from_city, to_city, depart_date
        ) latest
          ON latest.platform = fp.platform
         AND latest.from_city = fp.from_city
         AND latest.to_city = fp.to_city
         AND latest.depart_date = fp.depart_date
         AND latest.fetched_at = fp.fetched_at
        ORDER BY fp.from_city, fp.to_city, fp.depart_date, fp.price ASC
    """
    prices = {}
    try:
        with sqlite3.connect(db_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(query).fetchall()
    except sqlite3.Error:
        return {}

    for row in rows:
        if is_excluded_flight(row, flights_config):
            continue
        key = (row["from_city"].upper(), row["to_city"].upper(), row["depart_date"])
        current = prices.get(key)
        if current is None or float(row["price"]) < float(current["price"]):
            prices[key] = dict(row)
    return prices


def is_excluded_flight(row, flights_config):
    arrive_time = str(row["arrive_time"] or "")
    exclude_arrive_dates = set(flights_config.get("exclude_arrive_dates", []) or [])
    if any(arrive_time.startswith(date) for date in exclude_arrive_dates):
        return True

    if flights_config.get("direct_only", False):
        airline = str(row["airline"] or "")
        flight_no = str(row["flight_no"] or "")
        if "|" in airline or "|" in flight_no:
            return True
    return False


def get_flight_price_report(routes, latest_prices):
    rows = []
    for route in routes:
        from_name = route.get("from", "")
        to_name = route.get("to", "")
        origin = CITY_CODES.get(from_name, from_name).upper()
        destination = CITY_CODES.get(to_name, to_name).upper()
        date = route.get("date", "")
        target_price = int(route.get("target_price", 0) or 0)
        price = latest_prices.get((origin, destination, date))
        rows.append(
            {
                "from_name": from_name or CITY_NAMES.get(origin, origin),
                "to_name": to_name or CITY_NAMES.get(destination, destination),
                "origin": origin,
                "destination": destination,
                "date": date,
                "target_price": target_price,
                "price": price,
            }
        )

    priced_rows = [row for row in rows if row["price"]]
    hits = [
        row for row in priced_rows
        if float(row["price"]["price"]) <= row["target_price"]
    ]
    near = [
        row for row in priced_rows
        if float(row["price"]["price"]) > row["target_price"]
        and float(row["price"]["price"]) <= row["target_price"] + 150
    ]
    missing = [row for row in rows if not row["price"]]

    best = sorted(
        priced_rows,
        key=lambda row: (
            float(row["price"]["price"]) - row["target_price"],
            float(row["price"]["price"]),
        ),
    )[:4]

    latest_time = max(
        (row["price"]["fetched_at"] for row in priced_rows),
        default="暂无",
    )
    lines = [
        f"数据源：飞猪 JiPiao",
        f"最近更新：{latest_time}",
        "",
        f"命中：{len(hits)} 条｜接近：{len(near)} 条｜待更新：{len(missing)} 条",
    ]

    if hits:
        lines.append("")
        lines.append("### 低价命中")
        for row in sorted(hits, key=lambda item: float(item["price"]["price"])):
            lines.append(format_flight_row(row, status="可买"))

    lines.append("")
    lines.append("### 最值得盯")
    for row in best:
        lines.append(format_flight_row(row))

    if near:
        lines.append("")
        lines.append("### 接近目标")
        for row in sorted(near, key=lambda item: float(item["price"]["price"]) - item["target_price"]):
            lines.append(format_flight_row(row, status="差一点"))

    if missing:
        lines.append("")
        lines.append("### 暂无价格")
        for row in missing:
            lines.append(
                f"- {row['from_name']} -> {row['to_name']}｜{row['date']}｜目标 ¥{row['target_price']}"
            )

    return "\n".join(lines)


def format_flight_row(row, status=None):
    price = row["price"]
    current_price = int(float(price["price"]))
    gap = current_price - row["target_price"]
    if status is None:
        status = "低于目标" if gap <= 0 else f"差 ¥{gap}"
    flight = price.get("flight_no") or "航班待定"
    airline = price.get("airline") or "航司待定"
    depart_time = shorten_time(price.get("depart_time"))
    arrive_time = shorten_time(price.get("arrive_time"))
    time_text = f"｜{depart_time}-{arrive_time}" if depart_time and arrive_time else ""
    return (
        f"- {row['from_name']} -> {row['to_name']}｜{row['date']}｜"
        f"¥{current_price} / 目标 ¥{row['target_price']}｜{status}｜"
        f"{airline} {flight}{time_text}"
    )


def shorten_time(value):
    if not value:
        return ""
    text = str(value)
    return text[-5:] if len(text) >= 5 else text


def build_message(config):
    sections = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    sections.append(("今日简报", f"生成时间：{now}"))

    weather = config.get("weather", {})
    if weather.get("enabled"):
        sections.append(("天气", get_weather_report(weather)))

    news = config.get("news", {})
    if news.get("enabled"):
        sections.append(("新闻", get_news(news)))

    flights = config.get("flights", {})
    if flights.get("enabled"):
        sections.append(("机票", get_flights_note(flights)))

    body = []
    for heading, content in sections:
        body.append(f"## {heading}\n\n{content}")
    return "\n\n".join(body)


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


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_dotenv()
    config = load_config(args.config)
    title = config.get("title", "个人简报")
    content = build_message(config)

    if args.dry_run:
        print(f"# {title}\n\n{content}")
        return

    serverchan_sendkey = os.getenv("SERVERCHAN_SENDKEY", "").strip()
    pushplus_token = os.getenv("PUSHPLUS_TOKEN", "").strip()

    if serverchan_sendkey:
        print(send_serverchan(title, content, serverchan_sendkey))
    elif pushplus_token:
        print(send_pushplus(title, content, pushplus_token))
    else:
        raise SystemExit("请在 .env 中填写 SERVERCHAN_SENDKEY 或 PUSHPLUS_TOKEN")


if __name__ == "__main__":
    main()
