#!/usr/bin/env python3
"""
Сверяет ссылки geosite:/geoip: в конфиге с категориями в собранных .dat.

Ядро не стартует, если в подключённом .dat нет категории, на которую
ссылается конфиг. Конфиг живёт в подписке, файлы — в этом репозитории,
разойтись они могут молча. Проверка ловит это до публикации.

  python3 check-config.py dist xray-client-routing.json
  python3 check-config.py dist "https://sub.example.com/xxxx"

Источник — путь к файлу или URL подписки. Ответ подписки принимается
как JSON или как base64 с JSON внутри.
"""
import base64, json, os, sys, urllib.request

# Remnawave выбирает формат ответа по User-Agent (Xray-клиенты ловятся
# регулярным `^Happ/`), поэтому проверять надо ровно тот ответ, который
# получает телефон. Но в истории запросов подписки эта запись должна быть
# отличима от настоящего клиента, иначе она засоряет статистику подключений.
UA = os.environ.get("CHECK_UA", "Happ/1.0 (routing-ci; +github.com/nifoleyarc/routing)")


def fetch(src):
    if src.startswith(("http://", "https://")):
        req = urllib.request.Request(src, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode(errors="replace")
    return open(src, encoding="utf-8").read()


def parse(text):
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    try:
        return json.loads(base64.b64decode(text + "=" * (-len(text) % 4)))
    except Exception:
        sys.exit("не удалось разобрать источник ни как JSON, ни как base64+JSON")


def refs(node, out):
    """Собирает все geosite:/geoip: из любой вложенности."""
    if isinstance(node, str):
        for kind in ("geosite", "geoip"):
            if node.startswith(kind + ":"):
                out[kind].add(node.split(":", 1)[1].upper())
    elif isinstance(node, list):
        for x in node:
            refs(x, out)
    elif isinstance(node, dict):
        for x in node.values():
            refs(x, out)
    return out


def built(dat_dir):
    sys.path.insert(0, __file__.rsplit("/", 1)[0] if "/" in __file__ else ".")
    from trim import top_level, entry_name
    res = {}
    for kind in ("geosite", "geoip"):
        data = open(f"{dat_dir}/{kind}.dat", "rb").read()
        res[kind] = {entry_name(r) for fn, r in top_level(data) if fn == 1}
    return res


def main(dat_dir, sources):
    have = built(dat_dir)
    print(f"собрано: geosite {len(have['geosite'])}, geoip {len(have['geoip'])}")

    bad = False
    for src in sources:
        shown = src.split("//")[-1].split("/")[0] if "//" in src else src
        want = refs(parse(fetch(src)), {"geosite": set(), "geoip": set()})
        if not want["geosite"] and not want["geoip"]:
            print(f"\n{shown}: ссылок geosite:/geoip: не найдено — источник тот?")
            bad = True
            continue
        print(f"\n{shown}: ссылается на geosite {len(want['geosite'])}, geoip {len(want['geoip'])}")
        for kind in ("geosite", "geoip"):
            missing = want[kind] - have[kind]
            if missing:
                bad = True
                print(f"  !! НЕТ В {kind}.dat: {', '.join(sorted(missing))}")
        if not bad:
            print("  все категории на месте")

    if bad:
        print("\nЯдро на таком сочетании не запустится. Публикация отменена.")
        return 1
    print("\nконфиг и geo-файлы согласованы")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    sys.exit(main(sys.argv[1], sys.argv[2:]))
