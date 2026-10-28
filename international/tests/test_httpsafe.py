import tempfile
import unittest
from pathlib import Path

import dbhelp  # noqa: F401
from httpsafe import AbrufFehler, SichererClient, atomar_speichern, offene_adresse_pruefen

UA = "Test robin@example.org"


def transport_aus(antworten):
    it = iter(antworten)

    def t(url, headers, timeout):
        a = next(it)
        return a if not callable(a) else a()
    return t


class Allowlist(unittest.TestCase):
    def client(self, antworten, **kw):
        schlaf = []
        c = SichererClient({"data.sec.gov"}, user_agent=UA, transport=transport_aus(antworten), schlafen=schlaf.append, min_abstand=0, **kw)
        c.schlaf = schlaf
        return c

    def test_user_agent_mit_kontakt_pflicht(self):
        with self.assertRaises(AbrufFehler):
            SichererClient({"data.sec.gov"}, user_agent="anonym")

    def test_nur_https_und_allowlist(self):
        c = self.client([])
        for url in ("http://data.sec.gov/x", "https://evil.example/x", "https://data.sec.gov:8443/x", "https://user:pw@data.sec.gov/x",
                    "https://data.sec.gov.evil.example/x", "https://127.0.0.1/x"):
            with self.assertRaises(AbrufFehler, msg=url):
                c.holen(url)

    def test_weiterleitung_auf_interne_adresse_wird_nicht_gefolgt(self):
        c = self.client([(302, {"Location": "https://169.254.169.254/latest/meta-data"}, iter([]))])
        with self.assertRaisesRegex(AbrufFehler, "Weiterleitung"):
            c.holen("https://data.sec.gov/x")

    def test_groessenlimit(self):
        c = self.client([(200, {}, iter([b"x" * 600, b"x" * 600]))], max_bytes=1000)
        with self.assertRaisesRegex(AbrufFehler, "größer"):
            c.holen("https://data.sec.gov/x")

    def test_retry_after_und_begrenzter_backoff(self):
        c = self.client([(429, {"Retry-After": "7"}, iter([])), (503, {}, iter([])), (200, {}, iter([b"ok"]))], max_versuche=3)
        self.assertEqual(c.holen("https://data.sec.gov/x"), b"ok")
        self.assertIn(7.0, c.schlaf)

    def test_retry_ist_begrenzt(self):
        c = self.client([(429, {}, iter([]))] * 3, max_versuche=3)
        with self.assertRaises(AbrufFehler):
            c.holen("https://data.sec.gov/x")

    def test_403_wird_nicht_umgangen(self):
        c = self.client([(403, {}, iter([]))])
        with self.assertRaisesRegex(AbrufFehler, "403"):
            c.holen("https://data.sec.gov/x")

    def test_abgebrochener_download_liefert_nichts(self):
        def kaputt():
            yield b"teil"
            raise ConnectionResetError("abgebrochen")
        c = self.client([(200, {}, kaputt())])
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ConnectionResetError):
                daten = c.holen("https://data.sec.gov/x")
                atomar_speichern(d, "a.json", daten)
            self.assertEqual(list(Path(d).iterdir()), [])

    def test_atomar_speichern_ohne_teildatei(self):
        with tempfile.TemporaryDirectory() as d:
            pfad, h = atomar_speichern(d, "a.json", b"{}")
            self.assertEqual(pfad.read_bytes(), b"{}")
            self.assertEqual([p.name for p in Path(d).iterdir()], ["a.json"])
            self.assertEqual(len(h), 64)


class OffeneAdressen(unittest.TestCase):
    @staticmethod
    def dns(*ips):
        return lambda host, port, proto=0: [(2, 1, 6, "", (ip, port)) for ip in ips]

    def test_private_und_sonderadressen_abgelehnt(self):
        for ip in ("127.0.0.1", "10.0.0.5", "192.168.1.1", "172.16.0.1", "169.254.169.254", "0.0.0.0", "100.64.0.1", "224.0.0.1",
                   "::1", "fc00::1", "fe80::1", "::ffff:127.0.0.1", "::ffff:10.0.0.1"):
            with self.assertRaises(AbrufFehler, msg=ip):
                offene_adresse_pruefen(ip)

    def test_hostname_der_auf_intern_zeigt(self):
        with self.assertRaises(AbrufFehler):
            offene_adresse_pruefen("intern.example", self.dns("10.1.2.3"))

    def test_rebinding_gemischte_antwort_abgelehnt(self):
        with self.assertRaises(AbrufFehler):
            offene_adresse_pruefen("mix.example", self.dns("93.184.216.34", "127.0.0.1"))

    def test_oeffentliche_adresse_ok(self):
        self.assertTrue(offene_adresse_pruefen("ok.example", self.dns("93.184.216.34")))


if __name__ == '__main__':
    unittest.main()
