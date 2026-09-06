#!/usr/bin/env python3
"""
Пишет диплинк маршрутизации в заголовок ответа подписки Remnawave.

Happ забирает routing-профиль из кастомного HTTP-заголовка `routing`
на ответе подписки. Профиль приезжает клиенту вместе с подпиской, и если
его LastUpdated больше сохранённого — клиент перекачивает geo-файлы сам.

  REMNAWAVE_URL=https://panel.example.com/api \
  REMNAWAVE_TOKEN=... python3 push-routing.py HAPP.DEEPLINK

Остальные заголовки сохраняются: читаем текущие, подменяем только `routing`.
"""
import json, os, sys, urllib.request, urllib.error

HEADER = "routing"


def call(url, token, method="GET", payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/json")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:400]
        # Тело ошибки печатаем, токен в нём не фигурирует.
        sys.exit(f"{method} {url} -> HTTP {e.code}: {body}")
    except urllib.error.URLError as e:
        sys.exit(f"{method} {url} -> недоступен: {e.reason}")


def main(path):
    base = os.environ["REMNAWAVE_URL"].rstrip("/")
    token = os.environ["REMNAWAVE_TOKEN"]
    url = f"{base}/subscription-settings"

    link = open(path, encoding="utf-8").read().strip()
    if not link.startswith("happ://"):
        sys.exit(f"{path}: не похоже на диплинк Happ")

    cur = call(url, token).get("response", {})
    uuid = cur.get("uuid")
    if not uuid:
        sys.exit("в ответе нет uuid настроек подписки")

    headers = cur.get("customResponseHeaders") or {}
    # Имя заголовка нечувствительно к регистру: выкидываем любой вариант,
    # иначе получится два конкурирующих заголовка.
    merged = {k: v for k, v in headers.items() if k.lower() != HEADER}
    if merged.get(HEADER) == link or headers.get(HEADER) == link:
        print("заголовок routing уже актуален")
        return
    merged[HEADER] = link

    call(url, token, "PATCH", {"uuid": uuid, "customResponseHeaders": merged})
    kept = len(merged) - 1
    print(f"routing обновлён ({len(link)} символов), прочих заголовков сохранено: {kept}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
