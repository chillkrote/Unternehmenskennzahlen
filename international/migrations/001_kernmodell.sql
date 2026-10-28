-- Kernmodell der internationalen Erweiterung (Schema "international"). Nur neue Objekte, kein DROP, keine Eingriffe in bestehende Daten.
-- Abweichungen von der Übergabe (jeweils begründet):
--   fact.reported_at      Einreichungs-/Veröffentlichungsdatum, damit "bekannt zum" und berichtigte Abschlüsse getrennt abfragbar sind
--   fact.provenance       Herkunftsangaben (Formular, Accession, Originalwert, Skalierung), getrennt von den fachlichen Dimensionen
--   metric.regulatory     aufsichtsrechtliche Kennzahlen (CET1, RWA ...) sind nur mit consolidation='regulatory' zulässig
--   ingestion_run.watermark  Wasserzeichen, wird nur nach erfolgreichem Commit geschrieben
--   Ausschluss-Constraint auf listing, damit sich Tickerzuordnungen (gleiche Börse, gleicher Ticker) zeitlich nicht überlappen
CREATE EXTENSION IF NOT EXISTS btree_gist;
CREATE SCHEMA IF NOT EXISTS international;

CREATE TABLE international.country (
  iso2 text PRIMARY KEY CHECK (iso2 ~ '^[A-Z]{2}$'),
  iso3 text UNIQUE CHECK (iso3 IS NULL OR iso3 ~ '^[A-Z]{3}$'),
  name text NOT NULL,
  oecd_from date,
  oecd_until date,
  CHECK (oecd_until IS NULL OR oecd_until >= oecd_from)
);

CREATE TABLE international.entity (
  id text PRIMARY KEY,                         -- bei deutschen Bestandsunternehmen die zentrale ID U000123 aus stammdaten/
  legal_name text NOT NULL,
  domicile text REFERENCES international.country(iso2),   -- Sitzland; NULL = unbekannt
  lei text UNIQUE CHECK (lei IS NULL OR lei ~ '^[A-Z0-9]{20}$'),
  sector text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE international.identifier (
  scheme text NOT NULL,                        -- ISIN, LEI, CIK, YAHOO_TICKER ...
  value text NOT NULL,
  entity_id text NOT NULL REFERENCES international.entity(id),
  PRIMARY KEY (scheme, value)
);
CREATE INDEX identifier_entity ON international.identifier(entity_id);

CREATE TABLE international.instrument (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  entity_id text NOT NULL REFERENCES international.entity(id),
  isin text UNIQUE CHECK (isin IS NULL OR isin ~ '^[A-Z]{2}[A-Z0-9]{9}[0-9]$'),
  kind text NOT NULL
);

CREATE TABLE international.listing (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  instrument_id bigint NOT NULL REFERENCES international.instrument(id),
  mic text NOT NULL CHECK (mic ~ '^[A-Z0-9]{4}$'),
  ticker text NOT NULL,
  currency text NOT NULL CHECK (currency ~ '^[A-Z]{3}$'),
  valid_from date NOT NULL,
  valid_until date,
  UNIQUE (mic, ticker, valid_from),
  CHECK (valid_until IS NULL OR valid_until >= valid_from),
  EXCLUDE USING gist (mic WITH =, ticker WITH =, daterange(valid_from, valid_until, '[]') WITH &&)
);

CREATE TABLE international.source_document (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  provider text NOT NULL,
  external_id text NOT NULL,
  url text NOT NULL,
  sha256 text NOT NULL CHECK (sha256 ~ '^[a-f0-9]{64}$'),
  object_key text NOT NULL,                    -- Pfad im Objektspeicher bzw. im Repo
  fetched_at timestamptz NOT NULL DEFAULT now(),
  published_at timestamptz,
  rights_status text NOT NULL DEFAULT 'unverified',
  UNIQUE (provider, external_id, sha256)
);

CREATE TABLE international.metric (
  code text PRIMARY KEY,
  description text NOT NULL,
  period_kind text NOT NULL CHECK (period_kind IN ('instant', 'duration')),
  unit_kind text NOT NULL CHECK (unit_kind IN ('money', 'ratio', 'count')),
  regulatory boolean NOT NULL DEFAULT false
);

CREATE TABLE international.fact (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  entity_id text NOT NULL REFERENCES international.entity(id),
  metric_code text NOT NULL REFERENCES international.metric(code),
  period_start date,
  period_end date NOT NULL,
  value numeric NOT NULL,
  unit text NOT NULL,                          -- ISO-4217-Code, 'ratio' (Dezimalquote, 15 % = 0.15) oder 'count'
  accounting_standard text NOT NULL,
  consolidation text NOT NULL CHECK (consolidation IN ('group', 'solo', 'regulatory', 'unknown')),
  dimensions jsonb NOT NULL DEFAULT '{}',
  source_id bigint NOT NULL REFERENCES international.source_document(id),
  source_fact_key text NOT NULL,
  mapping_version text NOT NULL,
  quality text NOT NULL CHECK (quality IN ('raw', 'validated', 'rejected')),
  reported_at date,
  provenance jsonb NOT NULL DEFAULT '{}',
  recorded_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (source_id, source_fact_key, mapping_version),
  CHECK (period_start IS NULL OR period_start <= period_end)
);
CREATE INDEX fact_lookup ON international.fact(entity_id, metric_code, period_end);

CREATE FUNCTION international.fact_validate() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE m international.metric%ROWTYPE;
BEGIN
  SELECT * INTO m FROM international.metric WHERE code = NEW.metric_code;
  IF m.period_kind = 'instant' AND NEW.period_start IS NOT NULL THEN
    RAISE EXCEPTION 'Stichtagswert % darf kein period_start haben', NEW.metric_code USING ERRCODE = 'check_violation';
  END IF;
  IF m.period_kind = 'duration' AND NEW.period_start IS NULL THEN
    RAISE EXCEPTION 'Zeitraumwert % braucht period_start', NEW.metric_code USING ERRCODE = 'check_violation';
  END IF;
  IF m.unit_kind = 'money' AND NEW.unit !~ '^[A-Z]{3}$' THEN
    RAISE EXCEPTION 'Geldwert % braucht ISO-Währung, nicht %', NEW.metric_code, NEW.unit USING ERRCODE = 'check_violation';
  END IF;
  IF m.unit_kind = 'ratio' AND NEW.unit <> 'ratio' THEN
    RAISE EXCEPTION 'Quote % muss Einheit ratio haben (Dezimalquote)', NEW.metric_code USING ERRCODE = 'check_violation';
  END IF;
  IF m.unit_kind = 'count' AND NEW.unit <> 'count' THEN
    RAISE EXCEPTION 'Zählwert % muss Einheit count haben', NEW.metric_code USING ERRCODE = 'check_violation';
  END IF;
  IF m.regulatory AND NEW.consolidation <> 'regulatory' THEN
    RAISE EXCEPTION 'aufsichtsrechtliche Kennzahl % nur mit consolidation=regulatory', NEW.metric_code USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER fact_validate BEFORE INSERT OR UPDATE ON international.fact
  FOR EACH ROW EXECUTE FUNCTION international.fact_validate();

-- Sicht "bekannt zum": je Entität, Kennzahl, Periode, Standard, Kreis und Dimension die zuletzt veröffentlichte, nicht verworfene Fassung.
-- p_as_of NULL = aktueller Stand. Berichtigte Abschlüsse bleiben als eigene Zeilen in fact erhalten.
CREATE FUNCTION international.fact_as_of(p_as_of date DEFAULT NULL)
RETURNS SETOF international.fact LANGUAGE sql STABLE AS $$
  SELECT DISTINCT ON (f.entity_id, f.metric_code, f.period_start, f.period_end, f.accounting_standard, f.consolidation, f.dimensions)
         f.*
    FROM international.fact f
    JOIN international.source_document s ON s.id = f.source_id
   WHERE f.quality <> 'rejected'
     AND (p_as_of IS NULL OR COALESCE(f.reported_at, s.fetched_at::date) <= p_as_of)
   ORDER BY f.entity_id, f.metric_code, f.period_start, f.period_end, f.accounting_standard, f.consolidation, f.dimensions,
            COALESCE(f.reported_at, s.fetched_at::date) DESC, f.id DESC
$$;
CREATE VIEW international.fact_current AS SELECT * FROM international.fact_as_of(NULL);

CREATE TABLE international.fx_rate (
  base text NOT NULL CHECK (base ~ '^[A-Z]{3}$'),
  quote text NOT NULL CHECK (quote ~ '^[A-Z]{3}$'),
  rate_date date NOT NULL,
  rate numeric NOT NULL CHECK (rate > 0),
  source_id bigint NOT NULL REFERENCES international.source_document(id),
  PRIMARY KEY (base, quote, rate_date, source_id)
);

CREATE TABLE international.ingestion_run (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  adapter text NOT NULL,
  started_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz,
  status text NOT NULL CHECK (status IN ('running', 'ok', 'failed')),
  imported_count integer NOT NULL DEFAULT 0,
  watermark jsonb,
  error_details jsonb
);
