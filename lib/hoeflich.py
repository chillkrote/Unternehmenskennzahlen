"""Höfliche Abrufe für die täglichen Crawler: ehrliche Kennung und robots.txt.

Die Kennung nennt Projekt und Repository; robots.txt wird je Host einmal geholt (Wartezeit kurz, Fehler = erlaubt)
und gilt für die Kennung bzw. "*". Das ersetzt keine Bot-Schutz-Umgehung: gesperrte Seiten bleiben gesperrt."""
import threading
import urllib.robotparser
from urllib.parse import urlparse

import requests

UA = "Unternehmenskennzahlen/1.0 (privates Forschungsprojekt; +https://github.com/chillkrote/Unternehmenskennzahlen)"
_cache, _sperre = {}, threading.Lock()


def erlaubt(url):
    """True, wenn robots.txt des Hosts den Abruf nicht untersagt (oder nicht abrufbar ist)."""
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.netloc:
        return False
    with _sperre:
        rp = _cache.get(p.netloc)
    if rp is None:
        rp = urllib.robotparser.RobotFileParser()
        try:
            r = requests.get(f"{p.scheme}://{p.netloc}/robots.txt", headers={"User-Agent": UA}, timeout=8)
            if r.status_code == 200 and "html" not in r.headers.get("content-type", "").lower():
                rp.parse(r.text.splitlines())
            else:
                rp.parse([])            # keine robots.txt: alles erlaubt
        except Exception:
            rp.parse([])
        with _sperre:
            _cache[p.netloc] = rp
    return rp.can_fetch(UA, url)
