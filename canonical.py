#!/usr/bin/env python3
"""
Канонический отпечаток .dat, устойчивый к перестановке записей.

Генератор Loyalsoldier выкладывает домены внутри категории в
недетерминированном порядке (обход мапы в Go), поэтому файл меняет хеш
каждую пересборку даже при нулевом изменении содержимого. Публиковать по
такому признаку — значит гонять клиентам одно и то же.

Отпечаток считается по отсортированным записям, поэтому перестановка на
него не влияет. Сами .dat при этом остаются побайтовой копией апстрима:
сортировка нужна только для вычисления.

  python3 canonical.py dist/geosite.dat dist/geoip.dat
"""
import hashlib, sys
from trim import top_level, entry_name


def digest(path):
    data = open(path, 'rb').read()
    cats = []
    for fn, raw in top_level(data):
        if fn != 1:
            continue
        h = hashlib.sha256()
        # Записи сортируются, длина пишется явно — иначе склейка соседних
        # записей могла бы дать тот же поток байт.
        for item in sorted(bytes(v) for f2, v in top_level(raw) if f2 == 2):
            h.update(len(item).to_bytes(4, 'big'))
            h.update(item)
        cats.append((entry_name(raw), h.hexdigest()))

    top = hashlib.sha256()
    for name, h in sorted(cats):
        top.update(f"{name}:{h}\n".encode())
    return top.hexdigest(), len(cats)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    for path in sys.argv[1:]:
        d, n = digest(path)
        print(f"{d}  {path.rsplit('/', 1)[-1]}  ({n} категорий)")
