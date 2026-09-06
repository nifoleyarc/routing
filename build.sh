#!/usr/bin/env bash
# Скачивает апстримы, собирает из них обрезанные geosite.dat / geoip.dat.
# Единственный источник правды по составу категорий — списки ниже.
# Любая категория, на которую ссылается xray-client-routing.json,
# обязана быть здесь: если ядро не находит категорию, оно не стартует.
set -euo pipefail

LOYAL_GEOSITE=https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geosite.dat
LOYAL_GEOIP=https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geoip.dat
ROS_GEOSITE=https://github.com/hydraponique/roscomvpn-geosite/releases/latest/download/geosite.dat
ROS_GEOIP=https://github.com/hydraponique/roscomvpn-geoip/releases/latest/download/geoip.dat

SRC=${SRC:-upstream}
OUT=${OUT:-dist}
mkdir -p "$SRC" "$OUT"

fetch() { echo "  <- $2"; curl -fsSL --retry 3 -o "$1" "$2"; }
fetch "$SRC/loyal-geosite.dat" "$LOYAL_GEOSITE"
fetch "$SRC/loyal-geoip.dat"   "$LOYAL_GEOIP"
fetch "$SRC/ros-geosite.dat"   "$ROS_GEOSITE"
fetch "$SRC/ros-geoip.dat"     "$ROS_GEOIP"

# --- geosite ---------------------------------------------------------------
# Из Loyalsoldier — всё, что у него полнее, чем у roscomvpn.
LOYAL_SITE=(
  # российское, в direct
  category-ru category-bank-ru category-gov-ru category-ecommerce-ru
  category-media-ru category-education-ru category-entertainment-ru
  yandex vk ozon wildberries x5 2gis rutube habr
  # российские СМИ под блокировкой РКН, в proxy
  category-media-ru-blocked
  # сервисы в direct: пуши, обновления, экономия трафика
  apple icloud microsoft twitch pinterest
  steam epicgames category-games
  # сервисы в proxy: ТСПУ и баны РКН
  youtube telegram github google-play discord spotify openai
  # в block
  category-ads win-spy
  # обязательное
  private
)
# Из roscomvpn — то, чего у Loyalsoldier нет вообще.
ROS_SITE=(
  whitelist category-geoblock-ru twitch-ads
  faceit riot origin escapefromtarkov
)

python3 trim.py geosite "$OUT/geosite.dat" \
  --from "$SRC/loyal-geosite.dat" "${LOYAL_SITE[@]}" \
  --from "$SRC/ros-geosite.dat"   "${ROS_SITE[@]}"

# --- geoip -----------------------------------------------------------------
# direct — RU+BY, слитые CIDR, 36k диапазонов: определение «российского» по IP.
# telegram у roscomvpn отсутствует, а MTProto по домену не ловится совсем.
ROS_IP=(direct private whitelist)
LOYAL_IP=(telegram)

python3 trim.py geoip "$OUT/geoip.dat" \
  --from "$SRC/ros-geoip.dat"   "${ROS_IP[@]}" \
  --from "$SRC/loyal-geoip.dat" "${LOYAL_IP[@]}"

# --- смоук-конфиг ----------------------------------------------------------
# Ссылается на каждую собранную категорию. Если хоть одной нет в .dat,
# ядро не стартует — CI поймает это до публикации.
sites=$(printf '"geosite:%s",' "${LOYAL_SITE[@]}" "${ROS_SITE[@]}")
ips=$(printf   '"geoip:%s",'   "${ROS_IP[@]}"     "${LOYAL_IP[@]}")
cat > "$OUT/smoke.json" <<JSON
{
  "log": { "loglevel": "warning" },
  "routing": { "rules": [
    { "type": "field", "domain": [${sites%,}], "outboundTag": "direct" },
    { "type": "field", "ip":     [${ips%,}],   "outboundTag": "direct" }
  ] },
  "outbounds": [ { "tag": "direct", "protocol": "freedom" } ]
}
JSON

echo
ls -l "$OUT"
( cd "$OUT" && sha256sum geosite.dat geoip.dat | tee sha256sum.txt )
