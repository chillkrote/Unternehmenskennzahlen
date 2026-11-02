-- Unternehmenstabelle (unternehmen-tabelle/Unternehmen_Tabelle.csv) als Tabellen im Schema international.
-- Nur neue Objekte, kein DROP. Unternehmens-IDs (U000123) bleiben der einzige Schlüssel für entity; Zeilen ohne ID haben keinen
-- Eintrag in entity (IDs vergibt nur stammdaten/ids.py) und werden über row_key geführt.
--   company_register   eine Zeile je Zeile der Tabelle (26.137), entity_id nur bei Unternehmen mit Repo-ID
--   company_alias      Aliase (stammdaten/unternehmen_aliase.csv, zusammengelegte Namen aus den Bereinigungsprotokollen)
--   review_flag        Prüfmarkierungen mit Code, Detail und, falls vorhanden, Entscheidung
--   register_import    welcher Dateistand zuletzt importiert wurde
CREATE TABLE international.company_register (
  row_key text PRIMARY KEY,                    -- stabil: ISIN:<isin> | LEI:<lei> | NAME:<land>|<normalisierter Name> (bei Kollision mit #n)
  row_no integer NOT NULL,                     -- Position in der Tabelle, für den Export in Originalreihenfolge
  entity_id text UNIQUE REFERENCES international.entity(id),   -- nur bei Unternehmen mit Repo-ID
  name text NOT NULL,
  legal_form text,
  country_name text NOT NULL,                  -- Landesname wie in der Tabelle ("USA", "South Korea", "Sonstige" ...)
  domicile text REFERENCES international.country(iso2),         -- nur wenn eindeutig auf ein bekanntes Land abbildbar
  seat text,
  isin text UNIQUE CHECK (isin IS NULL OR isin ~ '^[A-Z]{2}[A-Z0-9]{9}[0-9]$'),
  ticker text,
  exchange text,
  listed boolean NOT NULL,
  sector text NOT NULL,
  nace text,
  lei text UNIQUE CHECK (lei IS NULL OR lei ~ '^[A-Z0-9]{20}$'),
  register_no text,
  website text,
  is_bank boolean NOT NULL,
  indices text,
  description text,
  source_url text NOT NULL,
  active boolean NOT NULL DEFAULT true,        -- false = in der letzten importierten Tabelle nicht mehr enthalten
  imported_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX company_register_name ON international.company_register (lower(name));
CREATE INDEX company_register_land_sektor ON international.company_register (country_name, sector);

CREATE TABLE international.company_alias (
  alias text NOT NULL,
  row_key text NOT NULL REFERENCES international.company_register(row_key) ON DELETE CASCADE,
  kind text NOT NULL,                          -- name | id_alt | zusammengelegt | umbenannt ...
  source text NOT NULL,
  PRIMARY KEY (row_key, alias, kind)
);
CREATE INDEX company_alias_lookup ON international.company_alias (lower(alias));

CREATE TABLE international.review_flag (
  row_key text NOT NULL REFERENCES international.company_register(row_key) ON DELETE CASCADE,
  code text NOT NULL,
  detail text NOT NULL DEFAULT '',
  decision text,                               -- Entscheidung, falls schon getroffen (z. B. "getrennt gelassen")
  reason text,
  PRIMARY KEY (row_key, code, detail)
);
CREATE INDEX review_flag_code ON international.review_flag (code);

CREATE TABLE international.register_import (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  file text NOT NULL,
  sha256 text NOT NULL,
  rows integer NOT NULL,
  imported_at timestamptz NOT NULL DEFAULT now()
);

-- Eine ISIN darf nie bei mehreren Unternehmen stehen: gehört sie in instrument schon einem anderen Unternehmen, wird die Zeile abgewiesen.
CREATE FUNCTION international.company_register_check() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE andere text;
BEGIN
  IF NEW.isin IS NOT NULL THEN
    SELECT entity_id INTO andere FROM international.instrument WHERE isin = NEW.isin;
    IF andere IS NOT NULL AND andere IS DISTINCT FROM NEW.entity_id THEN
      RAISE EXCEPTION 'ISIN % gehört laut instrument zu %, nicht zu %', NEW.isin, andere, COALESCE(NEW.entity_id, 'einer Zeile ohne ID')
        USING ERRCODE = 'check_violation';
    END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER company_register_check BEFORE INSERT OR UPDATE ON international.company_register
  FOR EACH ROW EXECUTE FUNCTION international.company_register_check();

CREATE VIEW international.company_overview AS
SELECT r.row_key, r.row_no, r.entity_id AS unternehmen_id, r.name, r.country_name, r.sector, r.isin, r.ticker, r.listed, r.is_bank,
       (SELECT count(*) FROM international.review_flag f WHERE f.row_key = r.row_key AND f.decision IS NULL) AS offene_pruefmarken,
       (SELECT count(*) FROM international.fact x WHERE x.entity_id = r.entity_id) AS fakten
  FROM international.company_register r WHERE r.active;
