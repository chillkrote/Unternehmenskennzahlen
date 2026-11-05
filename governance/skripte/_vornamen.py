import csv,re
F=set("""Adela Agnieszka Aicha Alena Alessandra Alexandra Alice Amparo Anette Angela Angelika Anika Anita Anja Anja-Isabel Anke Ann-Kristin Ann-Sophie Anna Anne Anne-Laure Annemarie Annette Antje Ariane Astrid Ayten Barbara Beate Beatrix Belén Bettina Birgit Brigitte Britta Brona Carinne Carla Carmen Caroline Catherine Celia Christiane Christina Christine Claire-Marie Clara-Christina Clarissa Clarisse Claudia Coline Colleen Cornelia Dagmar Daniela Darleen Deborah Diana Doreen Doris Dorothea Donya-Florence Elaine Elisabeth Elizabeth Elke Eva Ertharin Esma Fiona Frauke Frederique Friederike Gabriela Gabriella Geisha Georgiana Gerlinde Gertrude Gesa Gina Grazia Grit Grita Hanna Heike Helen Helena Helene Helga Helle Hilde Hildegard Hiltrud Holly Ilka Inge Ingeborg Ingrid Ingrid-Helen Irene Iris Isabel Isabelle Jamila Janina Jeannette Jennifer Johanna Judith Julia Jutta Karen Karin Katarzyna Katharina Katherina Kathrin Katja Katrin Kerstin Khadija Kimberly Kirstin Kirsty Kristin Laura Lina Linda Lisa Liz Lori Louise Luise Maggie Maja Mandy Manja Manuela Margret Mari-Lizette Maria Maria-Regina Marianne Marie Marie-Anne Mariella Marion Martina María Maya Mayree Melanie Michelle Monika Nadia Nadine Nadège Nancy Natalie Nathalie Nicole Nina Nora Olga Pamela Pascale Patricia Petra Pia Rachel Raffaella Rashmy Rebecca Regina Renata Renate Rose Ruth Sabina Sabine Sabrina Sandra Sara Sarena Saskia Sharon Sherry Sibylle Sieglinde Sigrid Silke Silvia Sohaila Sonia Sonja Sophie Sopna Stefanie Stephanie Sujatha Susanne Sybille Sylvie Szilvia Tamara Tania Tanja Tatjana Ulrike Ursula Uta Ute Valeria Vanessa Vera Verena Veronica Veronika Victoria Yasmin Yvonne Zvezdana Xiaomei Saori Ferdije Jade """.split())
AMBIG=set("Alexis Chris Robin Jackie Kelly Shannon Andrea Gabriele Simone Nicola Dominique Joan Laurence Kim Asoka Keryn Maxi Claude Ilke Dow Ferri Fei Feiyu Hong Ching Chong Jing Kui Liming Ping Qi Shaojun Xiaoqun Mimon Ola Deniz Michele Rainier Jean Nikola Yves Jos Lawrence Ben Elmar Hagen Jos CEO KR ma D. -Ing. h.".split())

def fn(n):
    for t in n.replace('(',' ').split():
        if '.' in t or t.rstrip('.') in ('Dr','Prof','KR','h','c','mult','Ing','Mag','Dipl','med','jur','CEO','ma','MBA') or t.startswith('-'): continue
        return t
    return ''

# Manuelle Einstufungen je Person (Name -> (Geschlecht, Konfidenz, Beleg)); Recherche 05.11.2026
OVR = {
 'Andrea Orcel': ('m', 'hoch', 'Vorname Andrea (IT) männlich; öffentlich bekannt'),
 'Kim Schindelhauer': ('m', 'mittel', 'Websuche: AIXTRON-Lebenslauf/MarketScreener, männliche Formulierungen'),
 'Liming Chen': ('m', 'mittel', 'Websuche: BASF-Kandidatenprofil (IBM Greater China, "he")'),
 'Mimon Uhamou': ('m', 'mittel', 'Websuche: Siemens-Biografie (Betriebsrat), männliche Formulierung'),
 'Dominique Lembke': ('m', 'mittel', 'Websuche: KION/IG Metall, "Mr. Lembke"'),
 'Prof. Dr.-Ing. Tong Zhang': ('m', 'mittel', 'Websuche: Schaeffler-HV-Lebenslauf 2019, Professor Tongji University'),
 'Dominique Mohabeer': ('w', 'hoch', 'Angabe von Robin (eigene Recherche, 05.11.2026)'),
 'Hong Chow': ('w', 'hoch', 'Angabe von Robin (eigene Recherche, 05.11.2026)'),
 'Ping Xu': ('w', 'hoch', 'Angabe von Robin (eigene Recherche, 05.11.2026)'),
 'Dr Fei Yu Xu': ('w', 'hoch', 'Angabe von Robin (eigene Recherche, 05.11.2026)'),
 'Kui Jiang': ('m', 'mittel', 'Vorname Kui überwiegend männlich (Weichai-Manager)'),
 'Chong Lee Tan': ('m', 'mittel', 'Namensbestandteile Chong Lee überwiegend männlich'),
 'Joan Trían Riu': ('m', 'mittel', 'Vorname Joan im Katalanischen männlich'),
 'Chris Ward': ('m', 'mittel', 'Vorname Chris überwiegend männlich'),
 'Kelly Bennett': ('w', 'mittel', 'Vorname Kelly überwiegend weiblich'),
 'Shannon A. Johnston': ('w', 'mittel', 'Vorname Shannon überwiegend weiblich'),
 'Robin J. Stalker': ('m', 'hoch', 'Robin Stalker, ehemaliger adidas-Finanzvorstand, öffentlich bekannt'),
 'Robin Stalker': ('m', 'hoch', 'Robin Stalker, ehemaliger adidas-Finanzvorstand, öffentlich bekannt'),
 'Robin Johnson': ('m', 'mittel', 'Vorname Robin überwiegend männlich'),
 'Alexis von Hoensbroech': ('m', 'hoch', 'öffentlich bekannt (Alexis von Hoensbroech)'),
 'Jackie Joyner-Kersee': ('w', 'hoch', 'öffentlich bekannt (Leichtathletin)'),
 'Jing Ulrich': ('w', 'hoch', 'öffentlich bekannt (Investmentbankerin)'),
 'Sirma Boshnakova': ('w', 'hoch', 'Vorname Sirma weiblich'),
 'Prof. Dr. Feiyu Xu': ('w', 'hoch', 'öffentlich bekannt (KI-Forscherin, SAP)'),
 'Xiaoqun Clever-Steg': ('w', 'mittel', 'Vorname Xiaoqun/Doppelname Clever-Steg, Websuche nicht erfolgt'),
 'Deniz Filiz Acar': ('w', 'mittel', 'Zweitvorname Filiz weiblich'),
 'Keryn Lee James': ('w', 'hoch', 'öffentlich bekannt (Keryn James)'),
 'Dominique Leroy': ('w', 'hoch', 'öffentlich bekannt (ehem. Proximus-CEO)'),
 'Simone Menne': ('w', 'hoch', 'öffentlich bekannt (ehem. Lufthansa-CFO)'),
 'Dr. Ferri Abolhassan': ('m', 'hoch', 'öffentlich bekannt (T-Systems)'),
 'Claude Chèvre': ('m', 'hoch', 'Vorname Claude (FR) überwiegend männlich'),
 'Ola Källenius': ('m', 'hoch', 'öffentlich bekannt (Mercedes-Benz-CEO)'),
 'Dr. Asoka Wöhrmann': ('m', 'hoch', 'öffentlich bekannt (ex DWS-CEO)'),
 'Dow R. Wilson': ('m', 'hoch', 'öffentlich bekannt (Varian)'),
 'Maxi Leuchters': ('w', 'mittel', 'Vorname Maxi überwiegend weiblich'),
 'Michele Trogni': ('w', 'mittel', 'öffentlich bekannt (Michele Trogni, Managerin)'),
 'Nicola D. Lafrentz': ('w', 'hoch', 'Vorname Nicola im Deutschen weiblich'),
 'Laurence Mulliez': ('w', 'hoch', 'Vorname Laurence (FR) weiblich'),
}
OVR.update({n:(g,c,b) for n,g,c,b in [
 ('Elmar König','m','hoch','Vorname Elmar männlich'),('Jean Pierre Mustier','m','hoch','öffentlich bekannt (ex UniCredit-CEO)'),
 ('Lawrence Rosen','m','hoch','Vorname Lawrence männlich (Lawrence A. Rosen, ex Deutsche Post)'),('Lawrence A. Rosen','m','hoch','Vorname Lawrence männlich (Lawrence A. Rosen, ex Deutsche Post)'),
 ('Yves Müller','m','hoch','Vorname Yves männlich'),('Ching Pong Quek','m','mittel','Namensbestandteile Ching Pong überwiegend männlich'),
 ('Dr. Shaojun Sun','m','mittel','Vorname Shaojun überwiegend männlich'),('Dr. Rainier van Roessel','m','hoch','Vorname Rainier männlich'),
 ('Ben van Beurden','m','hoch','öffentlich bekannt (ex Shell-CEO)'),('Dr. Qi Lu','m','hoch','öffentlich bekannt (Qi Lu, ex Baidu/Microsoft)'),
 ('Ilke Hildegard Panzer','w','hoch','Zweitvorname Hildegard weiblich'),('Hagen Reimer','m','hoch','IG-Metall-Vertreter im Siemens-AR, Vorname Hagen männlich'),
 ('Jos Benschop','m','hoch','Vorname Jos (NL) männlich; ASML-Manager')]})
def schaetze(name):
    """-> (geschlecht 'w'/'m'/'', konfidenz, beleg)"""
    if name in OVR: return OVR[name]
    f = fn(name)
    if not f: return ('', 'unsicher', 'kein Vorname erkennbar')
    if f in F or f in ('Andrea', 'Simone', 'Gabriele', 'Nikola', 'Nicola', 'Dominique', 'Laurence', 'Maxi'):
        if f in ('Andrea', 'Simone', 'Gabriele', 'Nikola', 'Nicola'):
            return ('w', 'mittel', 'Vorname ' + f + ' im deutschen Sprachraum überwiegend weiblich')
        return ('w', 'hoch', 'Vorname ' + f + ' weiblich')
    if f in AMBIG:
        return ('', 'unsicher', 'Vorname ' + f + ' mehrdeutig, keine Recherche')
    return ('m', 'hoch', 'Vorname ' + f + ' männlich (nicht als weiblich eingestuft)')
