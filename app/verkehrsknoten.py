"""Weltkugel, Reiter Handel: die größten Seehäfen und Flughäfen der Welt -> data/verkehrsknoten.json.

Quellen (alle frei, kein Schlüssel):
 - Rangfolgen und Mengen: Wikipedia (CC BY-SA 4.0), Listen "List of busiest container ports" (TEU, zuletzt 2025),
   "List of busiest ports by cargo tonnage" (Kilotonnen, Stand 2022, Shanghai International Shipping Institute),
   "List of busiest airports by passenger traffic" und "... by cargo traffic" (ACI, 2025). Die Zahlen selbst stammen von
   Lloyd's List, World Shipping Council, SISI und ACI; übernommen wird nur Rang und Menge mit Quellenangabe.
 - Koordinaten Seehäfen: UN/LOCODE (UNECE, frei, über das Paket datasets/un-locode, ODC-PDDL), Treffer über Landescode und Name,
   Ausnahmen in HAFEN_ALIAS bzw. HAFEN_LAGE (von Hand, Lage genähert).
 - Koordinaten Flughäfen: OurAirports (gemeinfrei) über den IATA-Code.

    python3 app/verkehrsknoten.py [--cache ordner]     # --cache: Wikipedia-Rohtexte dort ablegen bzw. von dort lesen
"""
import argparse
import csv
import io
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HIER = Path(__file__).resolve().parent
ZIEL = HIER / "data/verkehrsknoten.json"
UA = "Bilanzvergleich-Terminal/1.0 (Datenabruf fuer Weltkugel; github.com/chillkrote/Unternehmenskennzahlen)"
WP = "https://en.wikipedia.org/w/index.php?title=%s&action=raw"
SEITEN = {"teu": "List_of_busiest_container_ports", "tonnen": "List_of_busiest_ports_by_cargo_tonnage",
          "pax": "List_of_busiest_airports_by_passenger_traffic", "fracht": "List_of_busiest_airports_by_cargo_traffic"}
LOCODE = "https://raw.githubusercontent.com/datasets/un-locode/main/data/code-list.csv"
OURAIRPORTS = "https://davidmegginson.github.io/ourairports-data/airports.csv"
ISO3_2 = {"CHN": "CN", "SGP": "SG", "KOR": "KR", "USA": "US", "ARE": "AE", "MYS": "MY", "NLD": "NL", "BEL": "BE", "DEU": "DE", "JPN": "JP",
          "VNM": "VN", "TWN": "TW", "THA": "TH", "IDN": "ID", "IND": "IN", "TUR": "TR", "SAU": "SA", "ESP": "ES", "BRA": "BR", "GBR": "GB",
          "MAR": "MA", "EGY": "EG", "OMN": "OM", "LKA": "LK", "PAN": "PA", "ITA": "IT", "GRC": "GR", "FRA": "FR", "RUS": "RU", "AUS": "AU",
          "CAN": "CA", "MEX": "MX", "PHL": "PH", "PAK": "PK", "ZAF": "ZA", "CHL": "CL", "COL": "CO", "PER": "PE", "ARG": "AR", "JAM": "JM",
          "HKG": "HK", "ISR": "IL", "SWE": "SE", "POL": "PL", "PRT": "PT", "BGD": "BD", "NGA": "NG", "KEN": "KE", "TZA": "TZ", "GHA": "GH",
          "DZA": "DZ", "UKR": "UA", "ECU": "EC", "URY": "UY", "DOM": "DO", "BHS": "BS", "MLT": "MT", "DNK": "DK", "FIN": "FI", "NOR": "NO",
          "JOR": "JO", "KWT": "KW", "QAT": "QA", "IRN": "IR", "IRQ": "IQ", "MMR": "MM", "KHM": "KH", "DJI": "DJ", "AGO": "AO", "CIV": "CI",
          "SEN": "SN", "TGO": "TG", "BEN": "BJ", "MOZ": "MZ", "CUB": "CU", "VEN": "VE", "GTM": "GT", "CRI": "CR", "HND": "HN", "SLV": "SV"}

# Name in der Liste (nach Bereinigung) -> Suchname im UN/LOCODE
HAFEN_ALIAS = {
    "Ningbo-Zhoushan": "Ningbo", "Ningbo Zhoushan": "Ningbo", "Zhoushan": "Zhoushan", "Guangzhou": "Guangzhou", "Qingdao": "Qingdao",
    "Busan": "Busan", "Ports of Johor": "Pelepas", "Tanjung Pelepas": "Pelepas", "Port Klang": "Port Klang", "Antwerp-Bruges": "Antwerpen",
    "Antwerp": "Antwerpen", "Hamburg": "Hamburg", "Jebel Ali": "Jebel Ali", "Dubai": "Jebel Ali", "Los Angeles": "Los Angeles",
    "Long Beach": "Long Beach", "Ho Chi Minh City": "Ho Chi Minh", "Saigon": "Ho Chi Minh", "Hai Phong": "Haiphong", "Haiphong": "Haiphong",
    "Cai Mep": "Cai Mep", "Laem Chabang": "Laem Chabang", "Tanjung Priok": "Jakarta", "Jakarta": "Jakarta", "Colombo": "Colombo",
    "Kaohsiung": "Kaohsiung", "Tokyo": "Tokyo", "Yokohama": "Yokohama", "Nagoya": "Nagoya", "Kobe": "Kobe", "Osaka": "Osaka",
    "Tangshan": "Tangshan", "Qinhuangdao": "Qinhuangdao", "Dalian": "Dalian", "Yingkou": "Yingkou", "Rizhao": "Rizhao", "Yantai": "Yantai",
    "Lianyungang": "Lianyungang", "Tianjin": "Tianjin", "Xiamen": "Xiamen", "Shenzhen": "Shenzhen", "Hong Kong": "Hong Kong",
    "Shanghai": "Shanghai", "Suzhou": "Suzhou", "Taicang": "Taicang", "Nanjing": "Nanjing", "Wuhan": "Wuhan", "Foshan": "Foshan",
    "Dongguan": "Dongguan", "Zhuhai": "Zhuhai", "Fuzhou": "Fuzhou", "Beibu Gulf": "Qinzhou", "Qinzhou": "Qinzhou", "Huanghua": "Huanghua",
    "Caofeidian": "Caofeidian", "Jingtang": "Tangshan", "Weifang": "Weifang", "Zhanjiang": "Zhanjiang", "Shantou": "Shantou",
    "Algeciras": "Algeciras", "Valencia": "Valencia", "Barcelona": "Barcelona", "Piraeus": "Piraeus", "Gioia Tauro": "Gioia Tauro",
    "Genoa": "Genova", "Marsa Maroc": "Casablanca", "Tanger-Med": "Tanger", "Tanger Med": "Tanger", "Tangier Med": "Tanger",
    "Port Said": "Port Said", "East Port Said": "Port Said", "Salalah": "Salalah", "Jeddah": "Jeddah", "King Abdullah": "King Abdullah",
    "Khor Fakkan": "Khor Fakkan", "Khalifa": "Abu Dhabi", "Abu Dhabi": "Abu Dhabi", "Mundra": "Mundra", "Nhava Sheva": "Nhava Sheva",
    "Jawaharlal Nehru": "Nhava Sheva", "Chennai": "Chennai", "Karachi": "Karachi", "Chittagong": "Chittagong", "Mumbai": "Mumbai",
    "Santos": "Santos", "Cartagena": "Cartagena", "Colon": "Cristobal", "Manzanillo": "Manzanillo", "Balboa": "Balboa", "Callao": "Callao",
    "San Antonio": "San Antonio", "Buenos Aires": "Buenos Aires", "Veracruz": "Veracruz", "Lazaro Cardenas": "Lazaro Cardenas",
    "New York": "New York", "New York and New Jersey": "New York", "Savannah": "Savannah", "Charleston": "Charleston", "Houston": "Houston",
    "Oakland": "Oakland", "Seattle": "Seattle", "Tacoma": "Tacoma", "Vancouver": "Vancouver", "Prince Rupert": "Prince Rupert",
    "Montreal": "Montreal", "Norfolk": "Norfolk", "Virginia": "Norfolk", "Baltimore": "Baltimore", "South Louisiana": "Reserve",
    "Rotterdam": "Rotterdam", "Bremerhaven": "Bremerhaven", "Le Havre": "Le Havre", "Felixstowe": "Felixstowe", "Southampton": "Southampton",
    "London Gateway": "London Gateway", "Gdansk": "Gdansk", "Gdańsk": "Gdansk", "Constanta": "Constanta", "Odesa": "Odesa", "Novorossiysk": "Novorossiysk",
    "Ust-Luga": "Ust-Luga", "Primorsk": "Primorsk", "Saint Petersburg": "Sankt-Peterburg", "St. Petersburg": "Sankt-Peterburg",
    "Singapore": "Singapore", "Port Hedland": "Port Hedland", "Dampier": "Dampier", "Newcastle": "Newcastle", "Gladstone": "Gladstone",
    "Hay Point": "Hay Point", "Richards Bay": "Richards Bay", "Durban": "Durban", "Lagos": "Lagos", "Lome": "Lome", "Lomé": "Lome",
    "Abidjan": "Abidjan", "Tema": "Tema", "Mombasa": "Mombasa", "Dar es Salaam": "Dar es Salaam", "Djibouti": "Djibouti",
    "Bandar Abbas": "Bandar Abbas", "Ras Tanura": "Ras Tanura", "Ruwais": "Ruwais", "Fujairah": "Fujairah", "Kuwait": "Shuwaikh",
    "Incheon": "Inchon", "Gwangyang": "Kwangyang", "Ulsan": "Ulsan", "Pohang": "Pohang", "Pyeongtaek": "Pyongtaek", "Taichung": "Taichung",
    "Keelung": "Keelung", "Manila": "Manila", "Subic": "Subic Bay", "Cebu": "Cebu", "Davao": "Davao", "Surabaya": "Surabaya",
    "Semarang": "Semarang", "Belawan": "Belawan", "Penang": "Penang", "Kuantan": "Kuantan", "Rotterdam-Maasvlakte": "Rotterdam",
    "Tanjung Pelepas": "Pelepas", "Hong Kong, China": "Hong Kong", "Dubai Ports": "Jebel Ali", "Gothenburg": "Goteborg",
    "Valparaiso": "Valparaiso", "Guayaquil": "Guayaquil", "Kingston": "Kingston", "Freeport": "Freeport", "Vitória": "Vitoria",
    "Paranaguá": "Paranagua", "Itajaí": "Itajai", "Navegantes": "Navegantes", "Rio Grande": "Rio Grande", "Itaqui": "Itaqui",
    "Tubarão": "Tubarao", "Ponta da Madeira": "Ponta da Madeira", "Sines": "Sines", "Lisbon": "Lisboa", "Leixões": "Leixoes",
    "Marseille": "Marseille", "Fos-sur-Mer": "Fos-sur-Mer", "Trieste": "Trieste", "Venice": "Venezia", "La Spezia": "La Spezia",
    "Ambarli": "Ambarli", "Mersin": "Mersin", "Izmir": "Izmir", "Haifa": "Haifa", "Ashdod": "Ashdod", "Alexandria": "Alexandria",
    "Damietta": "Damietta", "Sokhna": "Sokhna", "Ain Sokhna": "Sokhna", "Aqaba": "Aqaba", "Bejaia": "Bejaia", "Algiers": "Alger",
    "Dammam": "Dammam", "King Abdulaziz": "Dammam", "Sohar": "Sohar", "Muscat": "Muscat", "Duqm": "Duqm", "Colombo, Sri Lanka": "Colombo",
}
# Lage von Hand, wo der UN/LOCODE keinen Treffer liefert: Name -> (lon, lat)
HAFEN_LAGE = {
    "Jebel Ali Dubai": (55.03, 25.01), "Hong Kong": (114.12, 22.31), "Tanger-Med": (-5.50, 35.89), "Ho Chi Minh Saigon": (106.78, 10.77),
    "New York / New Jersey": (-74.07, 40.67), "Kaohsiung": (120.29, 22.57), "Mundra": (69.71, 22.74),
    "Nhava Sheva / Jawaharlal Nehru Mumbai": (72.95, 18.95), "Qinzhou": (108.62, 21.74), "Beibu Gulf": (108.62, 21.74), "Yingkou": (122.25, 40.67),
    "Manila": (120.96, 14.59), "Valencia": (-0.32, 39.44), "Santos": (-46.30, -23.98), "Algeciras": (-5.43, 36.13),
    "Tanjung Perak": (112.73, -7.20), "Savannah": (-81.14, 32.13), "Jiangyin": (120.27, 31.92), "Salalah": (54.01, 16.94), "Port Hedland": (118.58, -20.31)}
HAFEN_LAND = {"Tanger-Med": "MA", "Santos": "BR"}


def holen(url, versuche=4):
    for i in range(versuche):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=90)
            return r.read().decode("utf-8", "replace")
        except Exception as e:
            print("  Abruf %s fehlgeschlagen (%s), Versuch %d" % (url[:70], e, i + 1), file=sys.stderr)
            time.sleep(8 * (i + 1))
    raise SystemExit("Abruf nicht möglich: " + url)


def seite(schluessel, cache):
    f = Path(cache) / (SEITEN[schluessel] + ".txt") if cache else None
    if f and f.exists():
        return f.read_text(encoding="utf-8")
    t = holen(WP % SEITEN[schluessel])
    time.sleep(4)
    if f:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(t, encoding="utf-8")
    return t


def zahl(s):
    s = re.sub(r"<ref.*?(/>|</ref>)", "", s, flags=re.S)
    s = re.sub(r"\{\{(?:nts|0)\|?([^}]*)\}\}", r"\1", s)
    m = re.search(r"\d[\d,\.]*", s.replace("{{0}}", ""))
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def name(s):
    s = re.sub(r"\{\{nowrap\|(.*)\}\}", r"\1", s)
    s = re.sub(r"\{\{[^}]*\}\}", "", s)
    m = re.search(r"\[\[(?:[^\]|]*\|)?([^\]]+)\]\]", s)
    n = (m.group(1) if m else s).strip(" '|")
    return re.sub(r"^Port of ", "", n).strip()


def iso2(code):
    code = code.strip().upper()
    return ISO3_2.get(code, code if len(code) == 2 else None)


ISO3_ALT = {"GER": "DE", "UAE": "AE", "SIN": "SG", "KSA": "SA", "ROK": "KR", "ESP": "ES", "NED": "NL", "RSA": "ZA", "UK": "GB", "TPE": "TW", "VIE": "VN",
            "INA": "ID", "PHI": "PH", "GRE": "GR", "POR": "PT", "DEN": "DK", "SUI": "CH", "CHI": "CL", "URU": "UY", "ALG": "DZ", "MAS": "MY"}
# Spaltenjahre der Containertabelle (erste Spalte 2025, dann 2023, 2022, ...)
CONT_JAHRE = [2025, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015]


def land_von(s):
    m = re.search(r"\{\{\s*(?:flagicon\|)?\s*([A-Za-z]{2,3})\s*\}\}", s, re.I)
    if m:
        c = m.group(1).upper()
        return ISO3_ALT.get(c) or iso2(c)
    return None


def container(text):
    """Erste Tabelle: Rang, Hafen, Land, ...; Menge = jüngste vorhandene Spalte (2025, sonst 2023, ...), in tausend TEU"""
    t = text[:text.find("==See also==")]
    ausgabe = []
    for blk in t.split('|- align="right"')[1:]:
        zeilen = [z for z in blk.strip().split("\n") if z.strip()]
        if not zeilen:
            continue
        zellen = [c.strip() for c in zeilen[0].lstrip("|").split("||")]
        if len(zellen) < 3:
            continue
        mr = re.search(r"(\d+)\s*$", zellen[0])
        land = land_von(zellen[2]) or land_von(zeilen[0])
        if not mr or "[[" not in zellen[1]:
            continue
        wert, jahr = None, None
        for i, z in enumerate(zeilen[1:11]):
            w = zahl(re.sub(r"^\|", "", z)) if re.sub(r"^\|", "", z).strip() else None
            if w:
                wert, jahr = w, CONT_JAHRE[min(i, len(CONT_JAHRE) - 1)]
                break
        if wert and wert < 100:      # Quelle schreibt einmal "4.804" statt "4,804" (Tausender)
            wert *= 1000
        if wert:
            ausgabe.append({"rang": int(mr.group(1)), "name": name(zellen[1]), "land": land, "teu_tsd": wert, "teu_jahr": jahr})
    return ausgabe


def tonnen(text):
    abschn = text.split("==2018")[0].split("==2019")[0]
    ausgabe = []
    for blk in abschn.split("\n|-")[1:]:
        tk = [x.strip().lstrip("|").strip() for x in re.split(r"\n\||\|\|", blk) if x.strip().lstrip("|").strip()]
        if len(tk) < 4 or "[[" not in tk[1]:
            continue
        mr = re.match(r"(\d+)", tk[0])
        w = zahl(tk[3])
        if mr and w:
            ausgabe.append({"rang": int(mr.group(1)), "name": name(tk[1]), "land": land_von(tk[2]), "kt": w})
    return ausgabe


def flug(text, _unused=None):
    ab = text.split("==2024")[0]
    ausgabe = []
    for n, blk in enumerate(ab.split("\n|-")[1:], 1):
        m = re.search(r"\b([A-Z]{3})/([A-Z]{4})\b", blk)
        if not m:
            continue
        vorn, hinten = blk[:m.start()], blk[m.end():]
        mr = re.match(r"\W*(?:\{\{0\}\}\s*)*(\d+)\.?", vorn.strip().lstrip("|"))
        link = re.search(r"\[\[(?:[^\]|]*\|)?([^\]]+)\]\]", vorn[vorn.find("[["):]) if "[[" in vorn else None
        sauber = re.sub(r"<ref.*?(/>|</ref>)", "", hinten, flags=re.S)
        sauber = re.sub(r"\{\{0\}\}", "", sauber)
        nr = re.search(r"\d{1,3}(?:,\d{3})+", sauber)
        if link and nr:
            ausgabe.append({"rang": len(ausgabe) + 1, "name": link.group(1).strip(), "iata": m.group(1), "icao": m.group(2),
                            "wert": float(nr.group(0).replace(",", ""))})
    return ausgabe


def lade_locode():
    roh = holen(LOCODE)
    zeilen = list(csv.DictReader(io.StringIO(roh)))
    out = {}
    for r in zeilen:
        if not r["Coordinates"] or "1" not in r["Function"]:   # Funktion 1 = Seehafen
            continue
        mm = re.match(r"(\d{2})(\d{2})([NS]) (\d{3})(\d{2})([EW])", r["Coordinates"])
        if not mm:
            continue
        lat = (int(mm[1]) + int(mm[2]) / 60) * (1 if mm[3] == "N" else -1)
        lon = (int(mm[4]) + int(mm[5]) / 60) * (1 if mm[6] == "E" else -1)
        for n in {r["NameWoDiacritics"].lower(), r["Name"].lower()}:
            out.setdefault((r["Country"], n), (round(lon, 3), round(lat, 3), r["Country"] + r["Location"]))
    return out


def lage(h, loc):
    such = HAFEN_ALIAS.get(h["name"], h["name"]).lower()
    land = h["land"]
    if h["name"] in HAFEN_LAGE:
        return HAFEN_LAGE[h["name"]] + (None,)
    for (c, n), v in loc.items():
        if c == land and n == such:
            return v
    for (c, n), v in loc.items():                # Teiltreffer: "ningbo" in "ningbo-zhoushan"
        if c == land and (such in n.split() or such in n.replace("-", " ").split() or n.startswith(such + " ")):
            return v
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache")
    a = ap.parse_args()
    teu = container(seite("teu", a.cache))
    ton = tonnen(seite("tonnen", a.cache))
    pax = flug(seite("pax", a.cache), 1)
    fr = flug(seite("fracht", a.cache), 1)
    print("Container %d, Tonnen %d, Passagiere %d, Fracht %d" % (len(teu), len(ton), len(pax), len(fr)))
    loc = lade_locode()
    haefen = {}
    for q, liste, feld in (("teu", teu, "teu_tsd"), ("ton", ton, "kt")):
        for h in liste:
            k = (h["land"], h["name"].lower())
            e = haefen.setdefault(k, {"name": h["name"], "land": h["land"]})
            e[q + "_rang"] = h["rang"]
            e[feld] = h[feld]
            if "teu_jahr" in h:
                e["teu_jahr"] = h["teu_jahr"]
    ohne = []
    out_h = []
    for e in haefen.values():
        e["land"] = e["land"] or HAFEN_LAND.get(e["name"])
        l = lage(e, loc)
        if not l:
            ohne.append(e["name"] + " (" + str(e["land"]) + ")")
            continue
        e["lon"], e["lat"], e["locode"] = l
        out_h.append(e)
    print("Häfen mit Lage %d, ohne %d: %s" % (len(out_h), len(ohne), ohne))
    # Flughäfen
    ap_csv = {}
    for r in csv.DictReader(io.StringIO(holen(OURAIRPORTS))):
        if r["iata_code"]:
            ap_csv[r["iata_code"]] = (float(r["longitude_deg"]), float(r["latitude_deg"]), r["iso_country"], r["name"])
    fl = {}
    for q, liste in (("pax", pax), ("fracht", fr)):
        for f in liste:
            e = fl.setdefault(f["iata"], {"iata": f["iata"], "icao": f["icao"], "name": f["name"]})
            e[q + "_rang"] = f["rang"]
            e[q] = f["wert"]
    out_f, fehl = [], []
    for e in fl.values():
        c = ap_csv.get(e["iata"])
        if not c:
            fehl.append(e["iata"]); continue
        e["lon"], e["lat"], e["land"] = round(c[0], 3), round(c[1], 3), c[2]
        out_f.append(e)
    print("Flughäfen %d, ohne Lage: %s" % (len(out_f), fehl))
    out_h.sort(key=lambda e: e.get("teu_rang", 999))
    out_f.sort(key=lambda e: e.get("pax_rang", 999))
    ZIEL.write_text(json.dumps({
        "abruf": time.strftime("%Y-%m-%d"),
        "quellen": [
            {"name": "Wikipedia: List of busiest container ports (TEU, 2025; Lloyd's List, World Shipping Council)", "lizenz": "CC BY-SA 4.0", "url": "https://en.wikipedia.org/wiki/List_of_busiest_container_ports"},
            {"name": "Wikipedia: List of busiest ports by cargo tonnage (Kilotonnen, 2022; Shanghai International Shipping Institute)", "lizenz": "CC BY-SA 4.0", "url": "https://en.wikipedia.org/wiki/List_of_busiest_ports_by_cargo_tonnage"},
            {"name": "Wikipedia: List of busiest airports by passenger traffic / by cargo traffic (2025; ACI)", "lizenz": "CC BY-SA 4.0", "url": "https://en.wikipedia.org/wiki/List_of_busiest_airports_by_passenger_traffic"},
            {"name": "UN/LOCODE (Lage der Seehäfen), UNECE", "lizenz": "frei, Quellenangabe", "url": "https://unece.org/trade/uncefact/unlocode"},
            {"name": "OurAirports (Lage der Flughäfen)", "lizenz": "gemeinfrei", "url": "https://ourairports.com/data/"}],
        "haefen": out_h, "flughaefen": out_f}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    main()
