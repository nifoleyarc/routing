#!/usr/bin/env python3
"""
Сборка routing-профиля Happ и диплинка happ://routing/onadd/<base64>.

Профиль намеренно пустой по правилам: он несёт только ссылки на geo-файлы
и Tunnel DNS. Вся маршрутизация живёт в xray-client-routing.json.
Если заполнить DirectSites/ProxySites/BlockSites, профиль навяжет свою
маршрутизацию поверх конфига ядра.

  python3 make-deeplink.py --repo nifoleyarc/routing
  python3 make-deeplink.py --repo nifoleyarc/routing --channel jsdelivr
  python3 make-deeplink.py --base https://route.odynguard.xyz/geo
"""
import argparse, base64, json, time

CHANNELS = {
    "releases": "https://github.com/{repo}/releases/latest/download",
    "jsdelivr": "https://cdn.jsdelivr.net/gh/{repo}@release",
}


def profile(base, name):
    return {
        "Name": name,
        "GlobalProxy": "true",
        "UseChunkFiles": "false",

        # Tunnel DNS. Основной сплит всё равно описан в конфиге ядра,
        # здесь дублируется тот же выбор: AdGuard общий, Яндекс домашний.
        "RemoteDns": "94.140.14.14",
        "DomesticDns": "77.88.8.8",
        "RemoteDNSType": "DoH",
        "RemoteDNSDomain": "https://dns.adguard-dns.com/dns-query",
        "RemoteDNSIP": "94.140.14.14",
        "DomesticDNSType": "DoH",
        "DomesticDNSDomain": "https://common.dot.dns.yandex.net/dns-query",
        "DomesticDNSIP": "77.88.8.8",

        "Geoipurl": f"{base}/geoip.dat",
        "Geositeurl": f"{base}/geosite.dat",
        "LastUpdated": str(int(time.time())),

        "DnsHosts": {},
        "RouteOrder": "block-proxy-direct",

        # Пусто намеренно — см. docstring.
        "DirectSites": [], "DirectIp": [],
        "ProxySites": [], "ProxyIp": [],
        "BlockSites": [], "BlockIp": [],

        "DomainStrategy": "IPIfNonMatch",
        "FakeDNS": "false",
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", help="owner/name на GitHub")
    ap.add_argument("--channel", default="releases", choices=list(CHANNELS))
    ap.add_argument("--base", help="свой базовый URL вместо GitHub")
    ap.add_argument("--name", default="Nikothan Routing")
    ap.add_argument("-o", default="HAPP.DEEPLINK")
    a = ap.parse_args()

    if a.base:
        base = a.base.rstrip("/")
    elif a.repo:
        base = CHANNELS[a.channel].format(repo=a.repo)
    else:
        ap.error("нужен --repo или --base")

    p = profile(base, a.name)
    raw = json.dumps(p, ensure_ascii=False, separators=(",", ":")).encode()
    link = "happ://routing/onadd/" + base64.b64encode(raw).decode()

    with open(a.o, "w", encoding="utf-8", newline="\n") as f:
        f.write(link + "\n")

    print(f"geosite: {p['Geositeurl']}")
    print(f"geoip:   {p['Geoipurl']}")
    print(f"\n{a.o}: {len(link)} символов")
