#!/usr/bin/env python3
"""
Сборка geosite.dat / geoip.dat из нескольких апстримов под конкретный
набор категорий.

Работает без protobuf-библиотек: читает записи верхнего уровня,
оставляет нужные и переписывает их байт-в-байт. Атрибуты доменов,
типы правил, regexp и всё остальное сохраняются как есть.

  # один источник
  python3 trim.py geosite geosite.dat geosite-slim.dat category-ru yandex

  # несколько источников
  python3 trim.py geosite geosite-slim.dat \
      --from loyalsoldier.dat category-ru yandex apple \
      --from roscomvpn.dat   whitelist twitch-ads

Категории берутся из источников в порядке объявления. Если имя встречается
в двух источниках, это ошибка: нужно явно решить, чью версию брать, и убрать
лишнее из списка. Так же ошибкой считается ненайденная категория — иначе
ядро молча получит .dat, на котором откажется стартовать.
"""
import sys


def read_varint(b, i):
    r = s = 0
    while True:
        x = b[i]
        i += 1
        r |= (x & 0x7F) << s
        s += 7
        if not x & 0x80:
            return r, i


def write_varint(n):
    out = bytearray()
    while True:
        x = n & 0x7F
        n >>= 7
        if n:
            out.append(x | 0x80)
        else:
            out.append(x)
            return bytes(out)


def top_level(b):
    """Отдаёт (номер_поля, сырые_байты_записи) для каждой записи верхнего уровня."""
    i = 0
    while i < len(b):
        key, i = read_varint(b, i)
        fn, wt = key >> 3, key & 7
        if wt == 2:
            ln, i = read_varint(b, i)
            yield fn, b[i:i + ln]
            i += ln
        elif wt == 0:
            _, i = read_varint(b, i)
        else:
            raise ValueError(f"неподдерживаемый wire type {wt}")


def entry_name(raw):
    """Первое строковое поле записи — код категории/страны."""
    for fn, val in top_level(raw):
        if fn == 1:
            return val.decode()
    return None


def count_items(raw):
    return sum(1 for fn, _ in top_level(raw) if fn == 2)


def pick(src, keep):
    """Выбирает из файла записи с нужными именами.

    Возвращает (упакованные_байты, [(имя, число_записей)], множество_ненайденных).
    """
    keep = {k.upper() for k in keep}
    data = open(src, 'rb').read()
    out = bytearray()
    found, stats = set(), []

    for fn, raw in top_level(data):
        if fn != 1:
            continue
        name = entry_name(raw)
        if name in keep and name not in found:
            found.add(name)
            stats.append((name, count_items(raw)))
            out += write_varint((1 << 3) | 2) + write_varint(len(raw)) + raw

    return bytes(out), stats, keep - found


def build(dst, groups):
    """groups — список (путь_к_источнику, [категории])."""
    out = bytearray()
    taken = {}
    missing, failed = [], False

    for src, cats in groups:
        dupes = sorted({c.upper() for c in cats} & taken.keys())
        if dupes:
            print(f"\n  КОЛЛИЗИЯ ИМЁН между {taken[dupes[0]]} и {src}:",
                  ", ".join(dupes))
            print("  Уберите категорию из списка одного из источников.")
            failed = True
            continue

        blob, stats, gone = pick(src, cats)
        out += blob
        print(f"\n  {src}")
        for name, n in sorted(stats, key=lambda x: -x[1]):
            taken[name] = src
            print(f"    {name:<28} {n:>9,}")
        if gone:
            missing += sorted(gone)
            print("    НЕ НАЙДЕНО:", ", ".join(sorted(gone)))

    if missing or failed:
        if missing:
            print("\n  ИТОГО НЕ НАЙДЕНО:", ", ".join(missing))
        return False

    open(dst, 'wb').write(out)
    print(f"\n  {dst}: {len(taken)} категорий, {len(out) / 1048576:.2f} МБ")
    return True


def parse_args(argv):
    """Разбирает обе формы вызова. Возвращает (kind, dst, groups)."""
    kind = argv[0]
    if "--from" in argv:
        dst = argv[1]
        groups = []
        for tok in argv[2:]:
            if tok == "--from":
                groups.append([None, []])
            elif groups and groups[-1][0] is None:
                groups[-1][0] = tok
            elif groups:
                groups[-1][1].append(tok)
            else:
                raise SystemExit("категории до первого --from")
        for src, cats in groups:
            if not cats:
                raise SystemExit(f"у источника {src} пустой список категорий")
        return kind, dst, [(s, c) for s, c in groups]
    src, dst, *cats = argv[1:]
    return kind, dst, [(src, cats)]


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print(__doc__)
        sys.exit(1)
    kind, dst, groups = parse_args(sys.argv[1:])
    print(f"\n{kind} -> {dst}")
    sys.exit(0 if build(dst, groups) else 1)
