"""Pilot Governance: erzeugt die CSVs unter governance/ aus den Jahresabschluss-PDFs der Banken
(banken/bilanzvergleich-gj2025/dokumente/...). Seitenangaben = PDF-Seite (nicht aufgedruckte Seitenzahl).
Aufruf: python3 governance/skripte/pilot_banken.py   (aus dem Repo-Root)
Nur Angaben, die im Dokument stehen; nichts wird aus Vornamen auf das Geschlecht geschlossen."""
import csv, re, sys, os, unicodedata
OUT = os.path.join(os.path.dirname(__file__), '..')

from lib import *
from lib import slug, UNI, mitglieder, mandate, werdegang, verg, kenn, M, X, K

DOC = 'banken/bilanzvergleich-gj2025/dokumente/'
CB = (DOC + 'commerzbank-ag/commerzbank-ag-jahresabschluss-2025.pdf', 'commerzbank-ag')
DB = (DOC + 'deutsche-bank-ag/annual-financial-statements-of-deutsche-bank-ag-2025.pdf', 'deutsche-bank-ag')
HV = (DOC + 'unicredit-bank-gmbh-hypovereinsbank/20260313-unicredit-bank-gmbh-jahresabschluss-2025.pdf', 'unicredit-bank-gmbh-hypovereinsbank')

# ---------------- Commerzbank (Jahresabschluss HGB 2025) ----------------
for n, f, seit in [('Dr. Bettina Orlopp','Vorsitzende',''),('Michael Kotzbauer','stellv. Vorsitzender',''),('Sabine Mlnarsky','Mitglied',''),
                   ('Thomas Schaufler','Mitglied',''),('Carsten Schmitt','Mitglied','2025-02-19'),('Bernhard Spalt','Mitglied',''),('Christiane Vorspel-Rüter','Mitglied','')]:
    M(CB, 'Vorstand', n, f, seit=seit, seite=57)
AR_CB = [  # name, funktion, art, beruf, institution, seit, bis
 ('Prof. Dr. Jens Weidmann','Vorsitzender','Anteilseigner','Ehemaliger Präsident; Professor of Practice in Central Banking','Deutsche Bundesbank; Frankfurt School of Finance & Management','',''),
 ('Sascha Uebel','stellv. Vorsitzender','Arbeitnehmer','Bankkaufmann','Commerzbank AG','',''),
 ('Heike Anscheit','Mitglied','Arbeitnehmer','Bankkauffrau','Commerzbank AG','',''),
 ('Gunnar de Buhr','Mitglied','Arbeitnehmer','Bankkaufmann','Commerzbank AG','',''),
 ('Harald Christ','Mitglied','Anteilseigner','Geschäftsführender Gesellschafter','Christ Capital GmbH','',''),
 ('Dr. Frank Czichowski','Mitglied','Anteilseigner','Ehemaliger Senior Vice President / Treasurer','KfW Bankengruppe','',''),
 ('Sabine U. Dietrich','Mitglied','Anteilseigner','Ehemaliges Mitglied des Vorstands','BP Europa SE','',''),
 ('Dr. Jutta A. Dönges','Mitglied','Anteilseigner','Chief Financial Officer','Uniper SE','','2025-05-15'),
 ('Dr. Michael Gorriz','Mitglied','Anteilseigner','Ehemaliger Global Chief Information Officer','Standard Chartered Bank','2025-05-15',''),
 ('Burkhard Keese','Mitglied','Anteilseigner','Geschäftsführer','Artemis Gruppe','',''),
 ('Thomas Kühnl','Mitglied','Arbeitnehmer','Bankkaufmann','Commerzbank AG','',''),
 ('Sabine Lautenschläger-Peiter','Mitglied','Anteilseigner','Ehemaliges Mitglied des Direktoriums; ehem. Mitglied des Aufsichtsratsgremiums','Europäische Zentralbank; Single Supervisory Mechanism der EZB','2025-05-15',''),
 ('Maxi Leuchters','Mitglied','Arbeitnehmer','Referatsleiterin für Unternehmensrecht und Unternehmensführung','Hans-Böckler-Stiftung','',''),
 ('Daniela Mattheus','Mitglied','Anteilseigner','Rechtsanwältin und Managementberaterin','','',''),
 ('Nina Olderdissen','Mitglied','Arbeitnehmer','Bankkauffrau','Commerzbank AG','',''),
 ('Sandra Persiehl','Mitglied','Arbeitnehmer','Bankangestellte','Commerzbank AG','',''),
 ('Michael Schramm','Mitglied','Arbeitnehmer','Bankkaufmann','Commerzbank AG','',''),
 ('Caroline Seifert','Mitglied','Anteilseigner','Unternehmensberaterin für Transformation','','',''),
 ('Dr. Gertrude Tumpel-Gugerell','Mitglied','Anteilseigner','Ehemaliges Mitglied des Direktoriums','Europäische Zentralbank','','2025-05-15'),
 ('Kevin Voß','Mitglied','Arbeitnehmer (Gewerkschaft)','Gewerkschaftssekretär','ver.di Bundesverwaltung','',''),
 ('Frederik Werning','Mitglied','Arbeitnehmer (Gewerkschaft)','Gewerkschaftssekretär','Fachgruppe Bankgewerbe, ver.di Bezirk Münsterland','',''),
 ('Frank Westhoff','Mitglied','Anteilseigner','Ehemaliges Mitglied des Vorstands','DZ BANK AG','',''),
]
for n, f, art, beruf, inst, seit, bis in AR_CB:
    M(CB, 'Aufsichtsrat', n, f, art, seit, bis, 57, beruf + ((' – ' + inst) if inst else ''),
      'Zuordnung Arbeitnehmer laut Fußnote 1 (von den Arbeitnehmern gewählt)' if art.startswith('Arbeitnehmer') else '')
    werdegang.append(dict(person_id=slug(n), name=n, station=beruf, organisation=inst, zeitraum='lt. Dokument ausgeübter bzw. früherer Beruf', art='Beruf laut Organverzeichnis',
                          quelle_dokument=CB[0], seite=57))
mand_cb_v = [('Dr. Bettina Orlopp','b','Kreditanstalt für Wiederaufbau AöR','Frankfurt am Main','','bis 2025-12-31'),
 ('Dr. Bettina Orlopp','b','mBank S.A.','Warschau (PL)','Konzernmandat','bis 2025-02-27'),
 ('Michael Kotzbauer','b','Frankfurter Wertpapierbörse AöR','Frankfurt am Main','','seit 2025-03-06'),
 ('Sabine Mlnarsky','a','BVV Versicherungsverein des Bankgewerbes a.G.','Berlin','',''),
 ('Sabine Mlnarsky','b','BVV Pension Management GmbH','Berlin','',''),
 ('Sabine Mlnarsky','b','BVV Versorgungskasse des Bankgewerbes e.V.','Berlin','',''),
 ('Thomas Schaufler','a','SCHUFA Holding AG','Wiesbaden','',''),
 ('Thomas Schaufler','a','Commerz Real AG','Wiesbaden','Konzernmandat, Vorsitz',''),
 ('Thomas Schaufler','b','Aquila Capital Investmentgesellschaft mbH','Hamburg','Konzernmandat, Vorsitz','seit 2025-02-18'),
 ('Thomas Schaufler','b','Commerz Real Investmentgesellschaft mbH','Wiesbaden','Konzernmandat, Vorsitz',''),
 ('Thomas Schaufler','b','mBank S.A.','Warschau (PL)','Konzernmandat',''),
 ('Carsten Schmitt','b','mBank S.A.','Warschau (PL)','Konzernmandat','seit 2025-02-28'),
 ('Bernhard Spalt','a','Commerz Real AG','Wiesbaden','Konzernmandat, stellv. Vorsitz',''),
 ('Bernhard Spalt','b','Commerz Real Investmentgesellschaft mbH','Wiesbaden','Konzernmandat, stellv. Vorsitz',''),
 ('Bernhard Spalt','b','mBank S.A.','Warschau (PL)','Konzernmandat, stellv. Vorsitz',''),
 ('Bernhard Spalt','b','Österreichische Post Aktiengesellschaft','Wien (AT)','','')]
for n,t,g,s,f,gl in mand_cb_v: X(CB,n,t,g,s,f,gl,58)
mand_cb_a = [('Prof. Dr. Jens Weidmann','a','Münchener Rückversicherungs-Gesellschaft AG','München','',''),
 ('Gunnar de Buhr','a','BVV Pensionsfonds des Bankgewerbes AG','Berlin','stellv. Vorsitz',''),
 ('Gunnar de Buhr','a','BVV Versicherungsverein des Bankgewerbes a.G.','Berlin','stellv. Vorsitz',''),
 ('Gunnar de Buhr','b','BVV Versorgungskasse des Bankgewerbes e.V.','Berlin','',''),
 ('Gunnar de Buhr','b','BVV Pension Management GmbH','Berlin','stellv. Vorsitz',''),
 ('Harald Christ','a','Ernst Russ AG','Hamburg','Vorsitz',''),
 ('Dr. Frank Czichowski','b','FMS Wertmanagement AöR','München','',''),
 ('Dr. Frank Czichowski','b','Frontclear Clearing Corporation B.V. (FCC)','Amsterdam (NL)','',''),
 ('Dr. Frank Czichowski','b','Landwirtschaftliche Rentenbank','Frankfurt am Main','',''),
 ('Sabine U. Dietrich','a','H&R GmbH und Co. KGaA','Salzbergen','','bis 2025-05-27'),
 ('Sabine U. Dietrich','a','MVV Energie AG','Mannheim','',''),
 ('Dr. Jutta A. Dönges','a','TUI AG','Hannover','','(Commerzbank-AR bis 2025-05-15)'),
 ('Dr. Michael Gorriz','b','Temenos AG','Genf (CH)','',''),
 ('Dr. Michael Gorriz','b','Mox Bank Limited','Hongkong (CHN)','','bis 2025-05-15'),
 ('Dr. Michael Gorriz','b','Audax Financial Technology Pte. Ltd.','Singapur (SGP)','','bis 2025-10-17'),
 ('Burkhard Keese','a','Frankfurter Allgemeine Zeitung GmbH','Frankfurt am Main','','2025-02-01 bis 2025-06-30'),
 ('Burkhard Keese','b','Konzernmandate Lloyd\'s of London (9 Gesellschaften)','Aldershot/London (GB)','','bis 2025-04-30'),
 ('Maxi Leuchters','a','PSD Bank Rhein-Ruhr eG','Düsseldorf','',''),
 ('Daniela Mattheus','a','Deutsche Bahn AG','Berlin','',''),
 ('Daniela Mattheus','a','JENOPTIK AG','Jena','Vorsitz','Vorsitz seit 2025-12-30'),
 ('Daniela Mattheus','a','Cewe Stiftung & Co. KGaA','Oldenburg','',''),
 ('Dr. Gertrude Tumpel-Gugerell','b','Vienna Insurance Group AG','Wien (AT)','','(Commerzbank-AR bis 2025-05-15)'),
 ('Dr. Gertrude Tumpel-Gugerell','b','AT & S AG','Leoben (AT)','',''),
 ('Kevin Voß','a','NÜRNBERGER Allgemeine Versicherungs-AG','Nürnberg','','seit 2025-02-22'),
 ('Kevin Voß','a','NÜRNBERGER Lebensversicherung AG','Nürnberg','','seit 2025-05-09'),
 ('Frederik Werning','a','Atruvia Aktiengesellschaft','Münster','','')]
for n,t,g,s,f,gl in mand_cb_a: X(CB,n,t,g,s,f,gl,59)
K(CB,'ar_mitglieder_zahl',20,'Personen',57,'Stand 31.12.2025 (22 genannt, 2 ausgeschieden zum 15.5.2025)')
K(CB,'ar_arbeitnehmervertreter_zahl',10,'Personen',57,'laut Fußnote 1 "Von den Arbeitnehmerinnen und Arbeitnehmern gewählt"')
K(CB,'ar_gewerkschaftsvertreter_zahl',2,'Personen',57,'Gewerkschaftssekretäre ver.di (Voß, Werning); Hans-Böckler-Stiftung (Leuchters) nicht mitgezählt')
K(CB,'mitbestimmung_ar','paritätisch (10 von 20 Arbeitnehmervertreter)','',57,'Rechtsgrundlage (MitbestG) im Dokument nicht genannt; Einordnung aus Besetzung abgeleitet, in der Corporate-Governance-Erklärung gegenprüfen')
K(CB,'vorstand_mitglieder_zahl',7,'Personen',57,'Stand 31.12.2025')
K(CB,'vorstand_frauen_zahl','','Personen',57,'im Jahresabschluss nicht angegeben; Corporate-Governance-Erklärung/Geschäftsbericht ausstehend')
K(CB,'ar_frauen_zahl','','Personen',57,'im Jahresabschluss nicht angegeben; Corporate-Governance-Erklärung/Geschäftsbericht ausstehend')
K(CB,'pay_ratio','','',36,'im Jahresabschluss nicht angegeben; Vergütungsbericht (§ 162 AktG) ausstehend')
K(CB,'mitarbeiter_jahresdurchschnitt',25835,'Personen',36,'davon weiblich 12.143 (47,0 %); inkl. Ausland, ohne Auszubildende')
for gj, v, a in [(2025,17457,3993),(2024,10936,3780)]:
    verg.append(dict(unternehmen_id=CB[1], gj=gj, gremium='Vorstand', person_id='', name='Gesamt (alle Mitglieder)', betrag_tsd_eur=v, art='Gesamtbezüge § 285 Nr. 9a HGB (DRS 17)', quelle_dokument=CB[0], seite=36,
        bemerkung='enthält Langfrist-Komponenten früherer Jahre auch ausgeschiedener Mitglieder; ohne Langfrist-Komponenten für GJ2025' if gj==2025 else ''))
    verg.append(dict(unternehmen_id=CB[1], gj=gj, gremium='Aufsichtsrat', person_id='', name='Gesamt (alle Mitglieder)', betrag_tsd_eur=a, art='Gesamtbezüge § 285 Nr. 9a HGB', quelle_dokument=CB[0], seite=36, bemerkung=''))
verg.append(dict(unternehmen_id=CB[1], gj=2025, gremium='Vorstand', person_id='', name='Barwert Pensionsanwartschaften aktive Mitglieder', betrag_tsd_eur=9598, art='Pensionsanwartschaft (Barwert)', quelle_dokument=CB[0], seite=37, bemerkung='Vorjahr 11.764'))

# ---------------- Deutsche Bank (Jahresabschluss HGB 2025) ----------------
VB = [('Christian Sewing','Vorsitzender (CEO)','',''),('James von Moltke','President','',''),('Raja Akram','Mitglied','2026-01-01',''),
 ('Fabrizio Campelli','Mitglied','',''),('Dr. Marcus Chromik','Mitglied','2025-05-01',''),('Bernd Leukert','Mitglied','',''),
 ('Alexander von zur Mühlen','Mitglied','',''),('Laura Padovani','Mitglied','',''),('Claudio de Sanctis','Mitglied','',''),
 ('Rebecca Short','Mitglied','',''),('Prof. Dr. Stefan Simon','Mitglied','','2025-04-30'),('Olivier Vigneron','Mitglied','','2025-05-19')]
for n,f,s,b in VB: M(DB,'Vorstand',n,f,seit=s,bis=b,seite=53)
M_DB = DB
X(DB,'Bernd Leukert','a','Bertelsmann SE & Co.KGaA','', 'Mitglied Aufsichtsrat','',59)
X(DB,'Prof. Dr. Stefan Simon','b','Leop. Krawinkel GmbH & Co. KG','','Vorsitz Beirat','bis 2025-04-30',59)
X(DB,'Prof. Dr. Stefan Simon','b','The Clearing House Payments Company LLC','','Mitglied Aufsichtsrat','bis 2025-04-30',59)
ARDB = [  # name, funktion, art, beruf, seit, bis, seite
 ('Alexander Wynaendts','Vorsitzender','Anteilseigner','','','',56),
 ('Frank Schulze','stellv. Vorsitzender','Arbeitnehmer','Staff Council Member (Betriebsrat)','','',57),
 ('Prof. Dr. Norbert Winkeljohann','stellv. Vorsitzender','Anteilseigner','Self-employed Corporate Consultant, Norbert Winkeljohann Advisory & Investments','','',58),
 ('Susanne Bleidt','Mitglied','Arbeitnehmer','Staff Council Member (Betriebsrat)','','',56),
 ('Mayree Clark','Mitglied','Anteilseigner','','','',56),
 ('Jan Duscheck','Mitglied','Arbeitnehmer (Gewerkschaft)','Head of National Working Group Banking, ver.di','','',56),
 ('Manja Eifert','Mitglied','Arbeitnehmer','Staff Council Member (Betriebsrat)','','',56),
 ('Claudia Fieber','Mitglied','Arbeitnehmer','Staff Council Member (Betriebsrat)','','',56),
 ('Sigmar Gabriel','Mitglied','Anteilseigner','Former German Federal Government Minister','','',56),
 ('Florian Haggenmiller','Mitglied','Arbeitnehmer (Gewerkschaft)','Head of National Working Group ICT, ver.di','','',57),
 ('Timo Heider','Mitglied','Arbeitnehmer','Staff Council Member (Betriebsrat)','','',57),
 ('Dr. Klaus Moosmayer','Mitglied','','','2025-05-22','',57),
 ('Kirsty Roth','Mitglied','','Chief Operations and Technology Officer, Thomson Reuters Corporation','2025-05-22','',57),
 ('Gerlinde M. Siebert','Mitglied','','Global Head of Governance, Deutsche Bank AG','','',57),
 ('Yngve Slyngstad','Mitglied','','CEO Aker Asset Management AS (bis 30.6.2025); CEO ICP Asset Management AS (seit 1.6.2025)','','',57),
 ('Stephan Szukalski','Mitglied','Arbeitnehmer (Gewerkschaft)','Bundesvorsitzender Deutscher Bankangestellten-Verband (DBV)','','',57),
 ('John Alexander Thain','Mitglied','Anteilseigner','','','',57),
 ('Jürgen Tögel','Mitglied','Arbeitnehmer','Staff Council Member (Betriebsrat)','','',57),
 ('Michele Trogni','Mitglied','','CEO Zinnia Corporate Holdings, LLC (bis 12/2025); Senior Advisor Zinnia/Eldridge (seit 1.1.2026)','','',57),
 ('Dr. Dagmar Valcárcel','Mitglied','','','','2025-05-22',57),
 ('Dr. Theodor Weimer','Mitglied','','','','2025-05-22',57),
 ('Frank Witter','Mitglied','','','','',58)]
for n,f,art,beruf,s,b,sp in ARDB:
    M(DB,'Aufsichtsrat',n,f,art,s,b,sp,beruf,'Einordnung nach Funktionsbezeichnung im Mandatsverzeichnis; Gesamtzahl Arbeitnehmervertreter im Jahresabschluss nicht ausgewiesen' if art.startswith('Arbeit') else '')
    if beruf: werdegang.append(dict(person_id=slug(n),name=n,station=beruf,organisation='',zeitraum='lt. Dokument',art='Funktion laut Mandatsverzeichnis',quelle_dokument=DB[0],seite=sp))
MDB = [('Alexander Wynaendts','Air France-KLM Group S.A.','Member Board of Directors',''),('Alexander Wynaendts','Puissance Holding B.V.','Non-Executive Director (Chair bis 27.11.2025)',''),
 ('Alexander Wynaendts','Uber Payments B.V.','Non-Executive Director, Chair',''),('Alexander Wynaendts','Uber Technologies, Inc.','Member Board of Directors',''),
 ('Susanne Bleidt','Postbeamtenkrankenkasse','Member Advisory Board',''),('Susanne Bleidt','Postbank Filialvertrieb AG','Member Aufsichtsrat','Konzernmandat'),
 ('Mayree Clark','Ally Financial, Inc.','Member Board of Directors',''),('Mayree Clark','Allvue Systems Holdings, Inc.','Member Board of Directors','bis 2025-08-01'),
 ('Jan Duscheck','NÜRNBERGER Beteiligungs-AG','Member Aufsichtsrat','seit 2025-03-04'),
 ('Sigmar Gabriel','Heristo AG','Member Aufsichtsrat',''),('Sigmar Gabriel','Rheinmetall AG','Member Aufsichtsrat','seit 2025-05-13'),
 ('Sigmar Gabriel','Siemens Energy AG','Member Aufsichtsrat',''),('Sigmar Gabriel','Siemens Energy Management GmbH','Member Aufsichtsrat',''),
 ('Florian Haggenmiller','IBM Deutschland GmbH','Member Aufsichtsrat',''),('Florian Haggenmiller','IBM Central Holding GmbH','Member Aufsichtsrat',''),
 ('Timo Heider','BHW Bausparkasse AG','Deputy Chair Aufsichtsrat','Konzernmandat'),('Timo Heider','PCC Services GmbH der Deutschen Bank','Deputy Chair Aufsichtsrat','Konzernmandat'),
 ('Timo Heider','Pensionskasse der BHW Bausparkasse VVaG','Deputy Chair Aufsichtsrat','Konzernmandat'),
 ('John Alexander Thain','Aperture Investors LLC','Member Board of Directors',''),('John Alexander Thain','Pine Island Capital Partners LLC','Chairman','bis 2025-07-01'),
 ('John Alexander Thain','Pine Island New Energy Partners','Chairman','seit 2025-07-01'),('John Alexander Thain','Uber Technologies, Inc.','Member Board of Directors',''),
 ('Jürgen Tögel','BVV Versicherungsverein des Bankgewerbes a.G.','Member Aufsichtsrat',''),('Jürgen Tögel','BVV Versorgungskasse des Bankgewerbes e.V.','Member Aufsichtsrat',''),
 ('Jürgen Tögel','BKK Deutsche Bank AG','Member Advisory Board','Konzernmandat'),
 ('Michele Trogni','Everly Life, LLC','Member Non-Executive Board',''),('Michele Trogni','Zinnia Corporate Holdings, LLC','CEO und Chair of the Board','bis 2025-12-31'),
 ('Dr. Dagmar Valcárcel','amedes Holding GmbH','Member Aufsichtsrat',''),('Dr. Dagmar Valcárcel','Antin Infrastructure Partners S.A.','Member Board of Directors',''),
 ('Dr. Theodor Weimer','Knorr Bremse AG','Member Aufsichtsrat',''),
 ('Prof. Dr. Norbert Winkeljohann','Bayer AG','Vorsitz Aufsichtsrat',''),('Prof. Dr. Norbert Winkeljohann','Bohnenkamp AG','Vorsitz Aufsichtsrat',''),
 ('Prof. Dr. Norbert Winkeljohann','Georgsmarienhütte Holding GmbH','Member Aufsichtsrat','bis 2025-09-17'),('Prof. Dr. Norbert Winkeljohann','Sievert SE','Vorsitz Aufsichtsrat',''),
 ('Frank Witter','CGI Inc.','Member Board of Directors','bis 2026-01-28'),('Frank Witter','Traton SE','Member Aufsichtsrat','')]
for n,g,f,gl in MDB: X(DB,n,'b' if 'Board of Directors' in f else 'a',g,'',f,gl,57 if n in('Florian Haggenmiller','Timo Heider','John Alexander Thain','Jürgen Tögel','Michele Trogni','Dr. Dagmar Valcárcel','Dr. Theodor Weimer','Frank Witter') else (58 if 'Winkeljohann' in n else 56))
K(DB,'ar_gewerkschaftsvertreter_zahl',3,'Personen',57,'Duscheck, Haggenmiller (ver.di) und Szukalski (DBV) lt. Funktionsbezeichnung')
K(DB,'ar_betriebsraete_zahl',6,'Personen',57,'Staff Council Members (Schulze, Bleidt, Eifert, Fieber, Heider, Tögel)')
K(DB,'ar_arbeitnehmervertreter_zahl','','Personen',57,'im Jahresabschluss nicht ausgewiesen (Mitbestimmung nach MitbestG üblich: Hälfte der Sitze); Corporate-Governance-Erklärung ausstehend')
K(DB,'vorstand_mitglieder_zahl',12,'Personen',53,'im GJ2025 tätig gewesen (inkl. 2 Ausgeschiedene); Stand 31.12.2025: 10 Mitglieder (Akram seit 1.1.2026)')
K(DB,'vorstand_frauen_zahl','','Personen',53,'im Jahresabschluss nicht angegeben; Corporate-Governance-Bericht ausstehend')
K(DB,'ar_frauen_zahl','','Personen',56,'im Jahresabschluss nicht angegeben; Corporate-Governance-Bericht ausstehend')
K(DB,'pay_ratio','','',51,'im Jahresabschluss nicht angegeben; Vergütungsbericht ausstehend')
verg += [dict(unternehmen_id=DB[1], gj=2025, gremium='Vorstand', person_id='', name='Gesamt (alle Mitglieder)', betrag_tsd_eur=56173.105, art='Gesamtvergütung (€ 56.173.105)', quelle_dokument=DB[0], seite=51, bemerkung='Vorjahr 50.394.830 €'),
 dict(unternehmen_id=DB[1], gj=2025, gremium='Vorstand', person_id='', name='Zahlungen an ehemalige Mitglieder', betrag_tsd_eur=100496.514, art='Zahlungen ehemalige Mitglieder (€ 100.496.514)', quelle_dokument=DB[0], seite=51, bemerkung='Vorjahr 35.841.194 €'),
 dict(unternehmen_id=DB[1], gj=2025, gremium='Aufsichtsrat', person_id='', name='Gesamt (alle Mitglieder)', betrag_tsd_eur=7712.5, art='Gesamtvergütung (€ 7.712.500)', quelle_dokument=DB[0], seite=51, bemerkung='Vorjahr 7.775.000 €')]

# ---------------- UniCredit Bank GmbH / HypoVereinsbank (Jahresabschluss HGB 2025) ----------------
GF = [('Marion Höllinger','Sprecherin der Geschäftsführung (CEO)'),('René Babinsky','Head of Private Clients'),('Marion Bayer-Schiller','Head of Large Corporates'),
 ('Martin Brinckmann','Head of Small and Medium Corporates'),('Artur Gruca','Chief Digital & Operating Officer (CDOO)'),('Marco Iannaccone','Head of Client Solutions'),
 ('Georgiana Lazar-O’Callaghan','Head of People & Culture (inkl. Arbeit und Soziales gemäß § 27 Abs. 2 S. 2 MgVG)'),('Pierpaolo Montana','Chief Risk Officer (CRO)'),('Ljubisa Tesić','Chief Financial Officer (CFO)')]
for n,f in GF: M(HV,'Geschäftsführung',n,f,seite=61)
ARHV = [('Andrea Orcel','Vorsitzender','Anteilseigner','Group CEO und Head of Italy der UniCredit S.p.A.','','',62),
 ('Florian Schwarz','stellv. Vorsitzender','Arbeitnehmer','Mitarbeiter der UniCredit Bank GmbH','','',62),
 ('Dr. Bernd Metzner','stellv. Vorsitzender','Anteilseigner','seit 1.9.2025 Mitglied der Geschäftsführung (CFO) der Unternehmensgruppe Theo Müller S.e.c.s.; bis 31.8.2025 Mitglied des Vorstands (CFO) der Gerresheimer AG','','',62),
 ('Dr. Michael Diederich','Mitglied','Anteilseigner','Mitglied des Vorstands (CFO) und stellv. Vorstandsvorsitzender der FC Bayern München AG','','2025-03-25',62),
 ('Sabine Eckhardt','Mitglied','Anteilseigner','Aufsichtsrätin und Advisor (ehem. CEO Central Europe Jones Lang LaSalle SE und Vorstand ProSiebenSat.1 Media SE)','','2025-03-25',62),
 ('Sabine Heimbach','Mitglied','Anteilseigner','Politik- und Kommunikationsberaterin (vormals Geschäftsführerin und Mitglied des Vorstands des Bayerischen Bankenverbands e.V., stellv. Sprecherin der Bundesregierung a.D.)','','',62),
 ('Marcus Kramer','Mitglied','Anteilseigner','vormals Mitglied des Vorstands (CRO) der BayernLB','2025-03-25','',62),
 ('Fiona Melrose','Mitglied','Anteilseigner','Head of Group Strategy und ESG der UniCredit S.p.A.','','',62),
 ('Tanja Münchrath','Mitglied','Arbeitnehmer','Mitarbeiterin der UniCredit Bank GmbH Milan Branch','2025-03-25','',62),
 ('Sonia Nassar','Mitglied','Arbeitnehmer','','','2025-03-25',60),('Angelika Plauk','Mitglied','Anteilseigner','','2025-03-25','',60),
 ('Claudia Richter','Mitglied','Arbeitnehmer','','','',60),('Oliver Skrbot','Mitglied','Arbeitnehmer','','','',60),('Christian Staack','Mitglied','Arbeitnehmer','','','',60),
 ('Gregor Völkl','Mitglied','Arbeitnehmer','','','2025-03-25',60),('Lisa Wolf','Mitglied','Arbeitnehmer','','2025-03-25','',60)]
for n,f,art,beruf,s,b,sp in ARHV:
    M(HV,'Aufsichtsrat',n,f,art,s,b,60,beruf,'Zuordnung lt. Dokument (Anteilseigner-/Arbeitnehmerseite); Beruf aus Verzeichnis S. 62' if beruf else 'Zuordnung lt. Dokument S. 60')
    if beruf: werdegang.append(dict(person_id=slug(n),name=n,station=beruf,organisation='',zeitraum='lt. Dokument',art='Beruf/vorherige Funktion laut Organverzeichnis',quelle_dokument=HV[0],seite=62))
X(HV,'Andrea Orcel','b','EIS Group Inc., San Francisco (USA)','San Francisco (USA)','','',62)
X(HV,'Dr. Bernd Metzner','a','Gerresheimer Bünde GmbH','Bünde','stellv. Vorsitz','bis 2025-08-31',62); X(HV,'Dr. Bernd Metzner','a','Gerresheimer Regensburg GmbH','Regensburg','stellv. Vorsitz','bis 2025-08-31',62)
X(HV,'Dr. Bernd Metzner','a','Gerresheimer Tettau GmbH','Tettau','stellv. Vorsitz','bis 2025-08-31',62)
for g in ['Gerresheimer Glass Inc., Vineland (USA)','Centor US Holding Inc., Perrysburg (USA)','Centor Inc., Perrysburg (USA)','Centor Pharma Inc., Perrysburg (USA)','Sensile Medical AG, Olten (CH)']:
    X(HV,'Dr. Bernd Metzner','b',g,'','','bis 2025-08-31',62)
X(HV,'Dr. Michael Diederich','a','Ehrmann SE','Oberschönegg','','',62); X(HV,'Dr. Michael Diederich','b','akf bank GmbH & Co KG','Wuppertal','','',62); X(HV,'Dr. Michael Diederich','b','Bundesliga International GmbH','Frankfurt am Main','','',62)
X(HV,'Sabine Eckhardt','a','CECONOMY AG','Düsseldorf','','',62); X(HV,'Sabine Eckhardt','b','Edel SE & Co. KGaA','Hamburg','Vorsitz','',62)
K(HV,'ar_mitglieder_zahl',12,'Personen',60,'Stand 31.12.2025 laut Verzeichnis: Orcel, Schwarz, Metzner, Heimbach, Kramer, Melrose, Münchrath, Plauk, Richter, Skrbot, Staack, Wolf (Eckhardt, Diederich, Nassar, Völkl bis 25.3.2025)')
K(HV,'ar_arbeitnehmervertreter_zahl',6,'Personen',60,'Schwarz, Münchrath, Richter, Skrbot, Staack, Wolf; Aufsichtsrat paritätisch besetzt (6 Anteilseigner-/6 Arbeitnehmerseite)')
K(HV,'ar_gewerkschaftsvertreter_zahl','','Personen',60,'im Jahresabschluss nicht ausgewiesen')
K(HV,'mitbestimmung_ar','paritätisch (6 von 12 Arbeitnehmerseite)','',60,'Rechtsgrundlage laut Dokument nicht ausdrücklich genannt (Hinweis auf MgVG bei Arbeit und Soziales); Einordnung aus Besetzung abgeleitet')
K(HV,'geschaeftsfuehrung_mitglieder_zahl',9,'Personen',61,'Stand 31.12.2025')
K(HV,'geschaeftsfuehrung_frauen_zahl','','Personen',61,'nicht eindeutig aus dem Dokument ableitbar (nur die Funktionsbezeichnung "Sprecherin der Geschäftsführung" ist weiblich); Geschäftsbericht/Website ausstehend')
K(HV,'ar_frauen_zahl',6,'Personen',60,'abgeleitet aus den im Dokument verwendeten Formen (Anteilseignervertreterin: Heimbach, Melrose, Plauk; Vertreterin der Arbeitnehmerseite: Münchrath, Richter, Wolf); alle 12 Mitglieder tragen eine geschlechtsmarkierte Funktionsbezeichnung')
verg += [dict(unternehmen_id=HV[1], gj=2025, gremium='Geschäftsführung', person_id='', name='Gesamt (alle Mitglieder)', betrag_tsd_eur=10288, art='Gesamtbezüge (Fix 7.131; kurzfr. variabel 567; aktienbasiert 817; Leistungen nach Beendigung/Versorgung 1.773)', quelle_dokument=HV[0], seite=58, bemerkung='Vorjahr 10.630'),
 dict(unternehmen_id=HV[1], gj=2025, gremium='Aufsichtsrat', person_id='', name='Gesamt (AR-Tätigkeit)', betrag_tsd_eur=834, art='Vergütung für Aufsichtsratstätigkeit', quelle_dokument=HV[0], seite=58, bemerkung='zzgl. 945 T€ an Arbeitnehmervertreter für ihre Tätigkeit als Arbeitnehmer'),
 dict(unternehmen_id=HV[1], gj=2025, gremium='Frühere Geschäftsführung', person_id='', name='Gesamt (frühere Mitglieder und Hinterbliebene)', betrag_tsd_eur=37136, art='Gesamtbezüge', quelle_dokument=HV[0], seite=58, bemerkung='Vorjahr 34.136')]


