"""Packt eine Terminal-Seite (dist/*.fragment.html) für die Artifact-Vorschau unter 16 MB.

Große Daten- und Codeblöcke werden gzip-komprimiert und base64-kodiert eingebettet; ein kleines Startskript am Ende entpackt
sie im Browser (DecompressionStream) und führt danach die Skripte in ihrer ursprünglichen Reihenfolge aus. Die Dateien in
dist/ bleiben unkomprimiert; das Ergebnis ist nur für die Vorschau gedacht.

    python3 app/artifact_packen.py app/dist/weltkugel.fragment.html /pfad/weltkugel.artifact.html
"""
import base64
import gzip
import re
import sys

SKRIPT = re.compile(r'<script(?P<attr>[^>]*)>(?P<inhalt>.*?)</script>', re.S)

START = """<script>
(async () => {
  const roh = async b64 => { const bin = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
    return await new Response(new Blob([bin]).stream().pipeThrough(new DecompressionStream("gzip"))).text(); };
  for (const el of document.querySelectorAll('script[type="application/x-gz-json"]')) { el.textContent = await roh(el.textContent); el.type = "application/json"; }
  for (const el of document.querySelectorAll('script[type="application/x-spaeter"]')) {
    const s = document.createElement("script"); s.textContent = el.dataset.gz != null ? await roh(el.textContent) : el.textContent;
    el.replaceWith(s);
  }
})();
</script>"""


def packen(html, grenze=20000):
    def ersetzen(m):
        attr, inhalt = m.group("attr"), m.group("inhalt")
        if 'src=' in attr:
            return m.group(0)
        z = lambda s: base64.b64encode(gzip.compress(s.encode(), 9)).decode()
        if 'application/json' in attr:
            if len(inhalt) < grenze:
                return m.group(0)
            return "<script" + attr.replace("application/json", "application/x-gz-json") + ">" + z(inhalt) + "</script>"
        if "type=" in attr:
            return m.group(0)
        if len(inhalt) < grenze:
            return '<script type="application/x-spaeter"' + attr + ">" + inhalt + "</script>"
        return '<script type="application/x-spaeter" data-gz' + attr + ">" + z(inhalt) + "</script>"
    return SKRIPT.sub(ersetzen, html) + "\n" + START + "\n"


if __name__ == "__main__":
    quelle, ziel = sys.argv[1], sys.argv[2]
    aus = packen(open(quelle, encoding="utf-8").read())
    open(ziel, "w", encoding="utf-8").write(aus)
    print(f"{len(aus) / 1e6:.1f} MB -> {ziel}")
