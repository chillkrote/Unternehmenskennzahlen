"""Zentraler, abgesicherter HTTP-Abruf für die Adapter.

* Nur HTTPS, nur Hosts aus einer ausdrücklichen Allowlist (bekannte APIs); Weiterleitungen sind verboten.
* Identifizierender User-Agent mit echter Kontaktadresse aus der Umgebung (INTERNATIONAL_USER_AGENT oder SEC_USER_AGENT), Mindestabstand zwischen Anfragen,
  Timeout, maximale Antwortgröße, Retry-After und begrenzter Backoff bei 429/503.
* Die Antwort wird erst nach vollständigem Empfang (Größe und SHA-256 geprüft) atomar in den Objektspeicher geschrieben;
  ein abgebrochener Download hinterlässt keine Teildatei.
* offene_adresse_pruefen(): für Dokumentcrawler mit beliebigen Hosts. Lehnt private, Loopback-, Link-Local-, Multicast- und
  reservierte IPv4/IPv6-Adressen ab. Gegen DNS-Rebinding schützt das allein nicht; dafür gehört ein kontrollierter Egress-Proxy davor.
Kein Bot-Schutz wird umgangen: bei 403/Captcha bricht der Abruf mit Fehler ab.
"""
import hashlib
import ipaddress
import os
import socket
import time
from pathlib import Path
from urllib.parse import urlsplit


class AbrufFehler(Exception):
    pass


def offene_adresse_pruefen(host, aufloesen=socket.getaddrinfo):
    """Wirft AbrufFehler, wenn der Host auf eine nicht öffentliche Adresse zeigt (auch nur eine von mehreren)."""
    try:
        ip = ipaddress.ip_address(host)
        adressen = [ip]
    except ValueError:
        try:
            adressen = [ipaddress.ip_address(a[4][0]) for a in aufloesen(host, 443, proto=socket.IPPROTO_TCP)]
        except OSError as e:
            raise AbrufFehler(f"Host nicht auflösbar: {host}") from e
    if not adressen:
        raise AbrufFehler(f"Host ohne Adresse: {host}")
    for a in adressen:
        if isinstance(a, ipaddress.IPv6Address) and a.ipv4_mapped:
            a = a.ipv4_mapped
        if not a.is_global or a.is_multicast:
            raise AbrufFehler(f"Adresse {a} von {host} ist nicht öffentlich")
    return adressen


class SichererClient:
    def __init__(self, erlaubte_hosts, user_agent=None, max_bytes=50_000_000, timeout=30, min_abstand=0.2,
                 max_versuche=3, max_wartezeit=60, transport=None, schlafen=time.sleep, offen=False):
        self.erlaubte_hosts = frozenset(h.lower() for h in erlaubte_hosts)
        ua = user_agent or os.environ.get("INTERNATIONAL_USER_AGENT") or os.environ.get("SEC_USER_AGENT", "")
        if "@" not in ua:
            raise AbrufFehler("User-Agent mit Kontaktadresse nötig (Umgebungsvariable INTERNATIONAL_USER_AGENT oder SEC_USER_AGENT, z. B. 'Name name@example.org')")
        self.user_agent = ua
        self.max_bytes, self.timeout, self.min_abstand = max_bytes, timeout, min_abstand
        self.max_versuche, self.max_wartezeit = max_versuche, max_wartezeit
        self._transport = transport or self._requests_get
        self._schlafen = schlafen
        self._letzte = 0.0
        self.offen = offen

    @staticmethod
    def _requests_get(url, headers, timeout):
        import requests
        r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=False, stream=True)
        return r.status_code, dict(r.headers), r.iter_content(65536)

    def pruefe_url(self, url):
        t = urlsplit(url)
        if t.scheme != "https" or t.username or t.password or t.port not in (None, 443):
            raise AbrufFehler(f"Nur https ohne Zugangsdaten/Port erlaubt: {url}")
        host = (t.hostname or "").lower()
        if self.offen:
            offene_adresse_pruefen(host)
        elif host not in self.erlaubte_hosts:
            raise AbrufFehler(f"Host nicht in der Allowlist: {host}")
        return host

    def holen(self, url):
        """Gibt die vollständige Antwort als bytes zurück (Statuscode 200), sonst AbrufFehler."""
        self.pruefe_url(url)
        for versuch in range(1, self.max_versuche + 1):
            warte = self.min_abstand - (time.monotonic() - self._letzte)
            if warte > 0:
                self._schlafen(warte)
            self._letzte = time.monotonic()
            try:
                status, kopf, stuecke = self._transport(url, {"User-Agent": self.user_agent, "Accept-Encoding": "gzip"}, self.timeout)
                if status == 200:
                    daten = bytearray()
                    for s in stuecke:
                        daten += s
                        if len(daten) > self.max_bytes:
                            raise AbrufFehler(f"Antwort größer als {self.max_bytes} Bytes: {url}")
            except OSError as e:          # Verbindungsabbruch, Timeout (auch requests-Fehler): begrenzt wiederholen, nie Teildaten liefern
                if versuch == self.max_versuche:
                    raise AbrufFehler(f"Verbindungsfehler nach {versuch} Versuchen: {url}: {e!r}") from e
                self._schlafen(min(2.0 ** versuch, self.max_wartezeit))
                continue
            if status in (301, 302, 303, 307, 308):
                raise AbrufFehler(f"Weiterleitung nicht erlaubt ({status}): {url}")
            if status in (429, 503) and versuch < self.max_versuche:
                try:
                    wartezeit = float({k.lower(): v for k, v in kopf.items()}.get("retry-after", ""))
                except ValueError:
                    wartezeit = 2.0 ** versuch
                self._schlafen(min(wartezeit, self.max_wartezeit))
                continue
            if status != 200:
                raise AbrufFehler(f"HTTP {status} für {url}")
            return bytes(daten)
        raise AbrufFehler(f"Abruf ohne Erfolg nach {self.max_versuche} Versuchen: {url}")


def atomar_speichern(verzeichnis, name, daten: bytes):
    """Schreibt erst in eine temporäre Datei und benennt sie um; gibt (Pfad, sha256) zurück."""
    verzeichnis = Path(verzeichnis)
    verzeichnis.mkdir(parents=True, exist_ok=True)
    ziel = verzeichnis / name
    tmp = verzeichnis / (name + ".teil")
    tmp.write_bytes(daten)
    os.replace(tmp, ziel)
    return ziel, hashlib.sha256(daten).hexdigest()
