"""Abrufe für die Crawler, die nur öffentliche Ziele erreichen (Schutz vor SSRF).

Quellseiten sind fremde Inhalte: ein Link auf http://127.0.0.1/, http://169.254.169.254/ oder ein Host, der auf eine
interne Adresse zeigt, darf vom Rechner des Crawlers nicht abgerufen werden. Deshalb
  - gilt nur http/https,
  - müssen alle Adressen, auf die der Hostname auflöst, öffentlich (ip.is_global) sein,
  - werden Weiterleitungen einzeln verfolgt und jeder Sprung neu geprüft,
  - vergleicht host_gehoert_zu() Hostnamen exakt (gleich oder Subdomain), nie als Teilstring.
Rest-Risiko: DNS kann zwischen Prüfung und Abruf wechseln (Rebinding); für die täglichen Crawler auf GitHub-Runnern genügt das."""
import ipaddress
import socket
from urllib.parse import urljoin, urlparse

MAX_SPRUENGE = 5


def host_gehoert_zu(host, basis):
    """True, wenn host == basis oder eine Subdomain davon ("www.sap.com" gehört zu "sap.com", "sap.com.evil.net" nicht)."""
    host = (host or "").lower().rstrip(".").removeprefix("www.")
    basis = (basis or "").lower().rstrip(".").removeprefix("www.")
    return bool(basis) and (host == basis or host.endswith("." + basis))


def basisdomain(url):
    """Registrierbare Domain in grober Näherung: die letzten zwei Labels des Hosts (ohne Port)."""
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    return ".".join(host.split(".")[-2:])


def ist_oeffentlich(url):
    """True, wenn url http(s) ist und jede Adresse des Hosts öffentlich erreichbar ist (kein Loopback, privat, Link-Local, ...)."""
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        return False
    try:
        adressen = {a[4][0] for a in socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == "https" else 80), proto=socket.IPPROTO_TCP)}
    except (socket.gaierror, UnicodeError, OSError):
        return False
    try:
        return bool(adressen) and all(ipaddress.ip_address(a.split("%")[0]).is_global for a in adressen)
    except ValueError:
        return False


def get(session, url, **kw):
    """session.get mit Prüfung jedes Ziels einschließlich aller Weiterleitungen; wirft ValueError bei nicht öffentlichem Ziel."""
    kw.pop("allow_redirects", None)
    for _ in range(MAX_SPRUENGE + 1):
        if not ist_oeffentlich(url):
            raise ValueError(f"Ziel nicht öffentlich oder kein http(s): {url}")
        r = session.get(url, allow_redirects=False, **kw)
        if r.is_redirect and r.headers.get("location"):
            url = urljoin(r.url, r.headers["location"])
            r.close()
            continue
        return r
    raise ValueError("zu viele Weiterleitungen")
