# BMW i5 Agent

BMW i5 Agent ist ein FastAPI-, PostgreSQL- und n8n-basiertes System zur teilautomatisierten BMW-Haendlerkampagne. Das Projekt verwaltet Haendlerstammdaten, erzeugt Kampagnen fuer konkrete Fahrzeugkonfigurationen, steuert den Versand in Batches, registriert eingehende Antworten, extrahiert Angebote aus E-Mails oder PDF-Texten und bewertet Angebote im Kontext der gewuenschten Konfiguration.

Der aktuelle Schwerpunkt liegt auf einem robusten operativen Flow:

- eine aktive Kampagne zur Zeit
- steuerbarer Versand in Wellen
- eindeutiges Matching eingehender E-Mails zur Kampagne
- strukturierte Angebotsextraktion
- Preis- und Konfigurationsvergleich fuer Reaktionsentscheidungen in n8n

## Inhaltsverzeichnis

- [Ueberblick](#ueberblick)
- [Fachlicher Ablauf](#fachlicher-ablauf)
- [Systemarchitektur](#systemarchitektur)
- [Projektstruktur](#projektstruktur)
- [Screenshots](#screenshots)
- [Lokale Inbetriebnahme](#lokale-inbetriebnahme)
- [Konfiguration](#konfiguration)
- [API-Uebersicht](#api-uebersicht)
- [Dispatch in Wellen](#dispatch-in-wellen)
- [Inbound- und Offer-Flow](#inbound--und-offer-flow)
- [Datenmodell](#datenmodell)
- [Tests und Qualitaet](#tests-und-qualitaet)
- [n8n und vorhandene Workflows](#n8n-und-vorhandene-workflows)
- [Weitere Dokumentation](#weitere-dokumentation)

## Ueberblick

Das System bildet den Lebenszyklus einer BMW-Anfragekampagne fuer ein bestimmtes Fahrzeug ab:

1. Haendler werden importiert oder gepflegt.
2. Eine Kampagne wird aus einer BMW-Konfiguration angelegt.
3. Versandfaehige Haendlerkontakte werden batchweise geclaimt.
4. n8n oder ein anderer Dispatcher verschickt die Anfragen.
5. Versandresultate werden als `sent` oder `send-failed` zurueckgemeldet.
6. Eingehende E-Mails werden registriert und einer Kampagne bzw. einem Haendlerkontakt zugeordnet.
7. Preise und Konfigurationshinweise werden aus Mailtext oder PDF-Text extrahiert.
8. Angebote werden gespeichert, verglichen und fuer Folgeaktionen aufbereitet.

## Fachlicher Ablauf

### Outbound

Eine Kampagne repraesentiert eine konkrete Fahrzeugsuche. Zu dieser Kampagne werden fuer geeignete Haendler `campaign_dealer_contact`-Eintraege erzeugt. Diese Kontakte durchlaufen Versandstatus wie:

- `PENDING`
- `RESERVED`
- `SENT`
- `SEND_FAILED`
- `SEND_STATE_UNKNOWN`
- `SKIPPED`

`POST /api/campaigns/{campaign_id}/contacts/claim` reserviert nur die naechste Welle von Kontakten. Nur diese duerfen anschließend verschickt werden.

### Inbound

Eine eingehende E-Mail wird ueber `POST /api/inbound-emails` registriert. Die Zuordnung zur Kampagne erfolgt ueber mehrere Signale, zum Beispiel:

- Reply-Thread
- `In-Reply-To`
- `References`
- Kampagnen-Token im Betreff oder Mailinhalt

Danach kann die Angebotsauswertung ueber `POST /api/inbound-emails/{inbound_email_id}/extract-offer` gestartet werden.

### Offer Extraction

Die Extraktion unterscheidet unter anderem:

- echtes Kaufangebot
- Rueckfrage des Haendlers
- Leasing- oder Finanzierungsbeispiel ohne relevantes Kaufangebot
- unklare oder pruefpflichtige Nachricht

Bei einem erkannten Angebot liefert die API ein strukturiertes `offer`-Objekt mit:

- Preisfeldern
- Herkunft der Extraktion
- Qualitaets- und Evidenzdaten
- Fahrzeugkonfiguration im Angebot
- Preisvergleich gegen bereits vorhandene Kampagnenangebote

## Systemarchitektur

### Laufzeitkomponenten

- `bmw-agent-api`: FastAPI-Anwendung
- `postgres`: persistente relationale Datenbank
- `n8n`: Orchestrierung, Triggering und Debugging

### Technischer Stack

- Python 3.11
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL 17
- n8n
- Docker Compose

### Wichtige Services

- `CampaignService`: Kampagnenerstellung und Lebenszyklus
- `CampaignContactService`: Outbound-Claims, Inbound-Registrierung, Offer-Extraktion
- `CampaignDispatchService`: Versandstatus und Kampagnenabschluss
- `DealerService`: Haendlerverwaltung und Import
- `CampaignComparisonService`: Vergleich aller Angebote einer Kampagne
- `OfferComparisonService`: Match gegen Konfigurationsanforderungen

## Projektstruktur

```text
app/
  api/           FastAPI-Router
  database/      Session- und Base-Konfiguration
  entities/      SQLAlchemy-Modelle
  repositories/  Datenzugriff
  schemas/       Pydantic-Request/Response-Modelle
  services/      Fachlogik
  templates/     E-Mail-Templates
migrations/      Alembic-Migrationen
tests/           API-, Service- und Integrations-Tests
n8n/             Exportierte Workflows
docs/            Architektur-, Workflow- und Debug-Dokumentation
data/            lokale Daten fuer n8n und optionale Runtime-Daten
```

## Screenshots

Die README erwartet drei Workflow-Screenshots unter `docs/images/`:

- `docs/images/workflow-campaign-dispatch.png`
- `docs/images/workflow-test-reset-and-validation.png`
- `docs/images/workflow-inbound-offer-processing.png`
- `docs/images/api-docs-swagger.png`

### Kampagnenversand und Batch-Steuerung

Dieser Workflow zeigt den outbound-orientierten Kampagnenablauf mit Claiming, Versand, Versandbestaetigung, Dispatch-Status und Abschlussentscheidung.

![Kampagnenversand und Batch-Steuerung](docs/images/workflow-campaign-dispatch.png)

### Test-Reset und Validierung

Dieser Workflow deckt Testumgebungs-Reset, Validierung und den technischen Vorlauf fuer reproduzierbare Testlaeufe ab.

![Test-Reset und Validierung](docs/images/workflow-test-reset-and-validation.png)

### Inbound-Mail-Verarbeitung und Offer Extraction

Dieser Workflow zeigt die Verarbeitung eingehender E-Mails vom IMAP-Trigger ueber Registrierung und PDF-Extraktion bis zur Lowest-Offer-Entscheidung und Benachrichtigung.

![Inbound-Mail-Verarbeitung und Offer Extraction](docs/images/workflow-inbound-offer-processing.png)

### API-Dokumentation in Swagger UI

Die FastAPI-Anwendung stellt unter `http://localhost:8000/docs` eine interaktive Swagger-Oberflaeche bereit. Darin lassen sich alle relevanten Endpunkte, Schemas und Request-/Response-Modelle direkt pruefen.

![API-Dokumentation in Swagger UI](docs/images/api-docs-swagger.png)

## Lokale Inbetriebnahme

### Voraussetzungen

- Docker und Docker Compose

### Start

```bash
docker compose up -d --build
docker exec bmw-agent-api alembic upgrade head
```

Danach sind die Standardendpunkte lokal erreichbar:

- API: `http://localhost:8000`
- API-Doku: `http://localhost:8000/docs`
- n8n: `http://localhost:5678`
- Healthcheck: `http://localhost:8000/health`

### Wann ist `--build` noetig?

Ein Rebuild ist noetig, wenn sich Build-relevante Dateien geaendert haben, zum Beispiel:

- `Dockerfile`
- `requirements.txt`

Fuer reine Python-Code-Aenderungen unter `app/`, `tests/` oder `migrations/` reicht in der Regel ein Neustart des API-Containers, weil diese Verzeichnisse in den Container gemountet werden:

```bash
docker compose restart bmw-agent-api
```

## Konfiguration

Die wichtigste Runtime-Konfiguration kommt aus Umgebungsvariablen.

### Relevante Settings

- `DATABASE_URL`
- `TEST_DATABASE_URL`
- `APP_ENV`
- `SINGLE_CAMPAIGN_MODE`
- `ALLOW_TEST_RESET`
- `TEST_RESET_TOKEN`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `TZ`
- `GENERIC_TIMEZONE`
- `N8N_ENCRYPTION_KEY`
- `N8N_HOST`
- `N8N_PORT`
- `N8N_PROTOCOL`

### Beispiel fuer lokale Entwicklung

```env
POSTGRES_DB=bmw_agent_app
POSTGRES_USER=bmw_agent
POSTGRES_PASSWORD=change-me

DATABASE_URL=postgresql+psycopg://bmw_agent:change-me@postgres:5432/bmw_agent_app
TEST_DATABASE_URL=postgresql+psycopg://bmw_agent:change-me@postgres:5432/bmw_agent_test

APP_ENV=development
SINGLE_CAMPAIGN_MODE=true
ALLOW_TEST_RESET=true
TEST_RESET_TOKEN=change-me

TZ=Europe/Berlin
GENERIC_TIMEZONE=Europe/Berlin
N8N_ENCRYPTION_KEY=change-me
N8N_HOST=localhost
N8N_PORT=5678
N8N_PROTOCOL=http
```

## API-Uebersicht

Die FastAPI-Anwendung bindet folgende Router ein:

- `/dealers`
- `/api/dealers`
- `/campaigns`
- `/api/campaigns`
- `/api/campaign-contacts`
- `/api/inbound-emails`
- `/api/review-queue`
- `/offers`
- `/api/admin`

### Health

- `GET /health`

### Dealer

- `POST /dealers`
- `POST /dealers/import`
- `GET /dealers`
- `GET /dealers/count`
- `GET /dealers/statistics`
- `GET /dealers/{dealer_id}`
- `PATCH /dealers/{dealer_id}`
- `DELETE /dealers/{dealer_id}`
- `GET /api/dealers/debug-selection`

### Campaign Core

- `POST /campaigns`
- `GET /campaigns`
- `GET /campaigns/{campaign_id}`
- `PATCH /campaigns/{campaign_id}/status`
- `GET /campaigns/{campaign_id}/offers`
- `POST /campaigns/{campaign_id}/offers`
- `POST /campaigns/{campaign_id}/offers/extract`
- `GET /campaigns/{campaign_id}/comparison`

### Campaign Start und Dispatch

- `POST /api/campaigns/start`
- `POST /api/campaigns/from-config`
- `POST /api/campaigns/create-and-start`
- `GET /api/campaigns/latest-relevant`
- `POST /api/campaigns/{campaign_id}/contacts/claim`
- `GET /api/campaigns/{campaign_id}/dispatch-status`
- `POST /api/campaigns/{campaign_id}/complete`

### Inbound E-Mails

- `POST /api/inbound-emails`
- `POST /api/inbound-emails/{inbound_email_id}/extract-offer`
- `GET /api/inbound-emails/{inbound_email_id}/debug-match`
- `GET /api/inbound-emails/review-queue`
- `GET /api/review-queue`

### Admin/Test Reset

- `GET /api/admin/reset-status`
- `POST /api/admin/reset-test-state`

Die Admin-Reset-Endpunkte sind absichtlich nur in `development` und `test` verfuegbar und verlangen `X-Reset-Token`.

## Dispatch in Wellen

Das Projekt ist explizit fuer den Versand in Batches ausgelegt.

Empfohlener Ablauf:

1. `POST /api/campaigns/from-config`
2. `POST /api/campaigns/{campaign_id}/contacts/claim` mit `limit`
3. versende nur die geclaimten Kontakte
4. melde jeden Versand als `sent` oder `send-failed`
5. frage `GET /api/campaigns/{campaign_id}/dispatch-status` ab
6. claim die naechste Welle, solange `has_more_sendable_contacts = true`

### Bedeutung von `dispatch-status`

Der Endpoint `GET /api/campaigns/{campaign_id}/dispatch-status` liefert unter anderem:

- `pending`: noch nicht geclaimte, noch sendbare Kontakte
- `reserved`: bereits geclaimt, aber noch nicht als finaler Versandstatus verbucht
- `sent`: versendet
- `replied`: Antwort eingegangen
- `offer_extracted`: Angebot erfolgreich extrahiert
- `needs_review`: manuelle Pruefung erforderlich
- `send_failed`: Versand definitiv fehlgeschlagen
- `send_state_unknown`: Versandstatus unklar
- `has_more_sendable_contacts`: `true`, wenn noch `pending > 0`
- `can_complete`: `true`, wenn `pending + reserved + send_failed + send_state_unknown == 0`

### Wann ist `can_complete = true`?

Erst wenn aus Sicht des Dispatch keine offene Arbeit mehr existiert. Diese Status muessen auf `0` sein:

- `PENDING`
- `RESERVED`
- `SEND_FAILED`
- `SEND_STATE_UNKNOWN`

Diese Status blockieren `can_complete` dagegen nicht:

- `SENT`
- `REPLIED`
- `OFFER_EXTRACTED`
- `NEEDS_REVIEW`
- `SKIPPED`

Das ist bewusst so implementiert: Eine Kampagne kann fuer den Outbound abgeschlossen sein, obwohl Inbound-Verarbeitung und Angebotsauswertung noch weiterlaufen.

## Inbound- und Offer-Flow

### Registrierung eingehender E-Mails

`POST /api/inbound-emails` registriert eine Mail idempotent ueber `provider` und `provider_message_id`. Die Antwort enthaelt Matching-Informationen zur Kampagne.

### Extraktion

`POST /api/inbound-emails/{inbound_email_id}/extract-offer` analysiert:

- `text_body`
- `html_body` nach Normalisierung
- zusaetzlich uebergebenen `attachment_text`

### Extraktionsergebnis

Das Response-Modell liefert:

- `processing_result`
- `message_type`
- `confidence`
- `offer`
- `gross_final_price`
- `currency`
- `price_confidence`
- `needs_review`
- `review_reason`
- `dealer_offer_id`

Wenn ein Angebot erkannt wird, enthaelt `offer` typischerweise:

- `offer_type`
- `pricing`
- `source`
- `quality`
- `configuration`
- `price_comparison`

### Preisvergleich im Inbound-Flow

Die Extraktionsantwort enthaelt einen Preisvergleich gegen vorhandene Kampagnenangebote. Das ist fuer n8n gedacht, um sofort auf guenstige Antworten reagieren zu koennen.

Wichtige Felder:

- `current_offer_price`
- `previous_lowest_price`
- `lowest_price_in_campaign`
- `matches_or_beats_previous_lowest`
- `lower_than_previous_lowest`
- `equal_to_previous_lowest`
- `is_lowest_overall`
- `is_tied_lowest_overall`

Praxisregel:

- reagiere sofort, wenn `matches_or_beats_previous_lowest = true`
- priorisiere besonders, wenn `lower_than_previous_lowest = true`

### Konfigurationsdarstellung im Angebot

Innerhalb von `offer.configuration` werden zwei Sichten zusammengefuehrt:

- `requested`: die Kampagnenanforderung
- `extracted`: im Angebot erkannte Werte wie Variante oder Karosserie

Das ist die Grundlage fuer Angebotsvergleich und spaetere Ranking- oder Review-Entscheidungen.

## Datenmodell

Die wichtigsten Entitaeten sind:

- `dealer`: Haendlerstammdaten
- `campaign`: Kampagnenkopf
- `campaign_configuration`: Zielkonfiguration
- `configuration_requirement`: einzelne Muss-/Soll-Merkmale
- `campaign_dealer_contact`: Versand- und Antwortstatus pro Haendler
- `inbound_email`: eingehende Nachricht
- `dealer_offer`: extrahiertes Angebot
- `dealer_offer_feature`: normalisierte Merkmale eines Angebots

### Single-Campaign-Mode

Das Projekt laeuft aktuell im Single-Campaign-Mode. Fachlich zulaessig sind:

- keine Kampagne
- genau eine Kampagne

Mehrere parallele Kampagnen sind nicht vorgesehen. Die Absicherung erfolgt sowohl in der Service-Schicht als auch ueber Datenbank-Constraints. Details stehen in [docs/architecture/single_campaign_mode.md](docs/architecture/single_campaign_mode.md).

## Tests und Qualitaet

### Testausfuehrung

Empfohlen im Container:

```bash
docker exec bmw-agent-api pytest
```

Vorher sicherstellen:

```bash
docker exec bmw-agent-api alembic upgrade head
```

### Wichtiger Testschutz

Integrationstests duerfen nur gegen `TEST_DATABASE_URL` laufen. Ein Fallback auf `DATABASE_URL` ist absichtlich deaktiviert.

Beispiel:

```env
DATABASE_URL=postgresql+psycopg://bmw_agent:change-me@postgres:5432/bmw_agent_app
TEST_DATABASE_URL=postgresql+psycopg://bmw_agent:change-me@postgres:5432/bmw_agent_test
```

Wenn `TEST_DATABASE_URL` fehlt oder nicht auf eine Testdatenbank zeigt, bricht `pytest` mit einer klaren Fehlermeldung ab.

### Abgedeckte Bereiche

Die Test-Suite deckt unter anderem ab:

- Dealer-Import und Stammdaten-APIs
- Kampagnenerstellung aus Konfiguration
- Dispatch in Batches
- Completion-Logik
- Inbound-Matching
- Offer-Extraktion
- Preisvergleich und Ranking
- Alembic-Migrationen
- Schutzmechanismen fuer Test-Reset und Testdatenbank

## n8n und vorhandene Workflows

n8n ist die Orchestrierungs- und Debugging-Schicht des Projekts.

Vorhandene Workflow-Dateien:

- `n8n/BMW – Incoming Dealer Offers.json`
- `n8n/BMW – Dealer Database Debug.json`

Typische Aufgaben in n8n:

- Kampagne anlegen
- Versandwellen triggern
- Gmail/IMAP anbinden
- eingehende Antworten registrieren
- `extract-offer` aufrufen
- auf Preisvergleiche oder Review-Signale reagieren

## Weitere Dokumentation

- [docs/architecture/index.md](docs/architecture/index.md)
- [docs/architecture/single_campaign_mode.md](docs/architecture/single_campaign_mode.md)
- [docs/workflows/campaign_batch_dispatch.md](docs/workflows/campaign_batch_dispatch.md)
- [docs/workflows/campaign_completion.md](docs/workflows/campaign_completion.md)
- [docs/workflows/inbound_single_campaign_matching.md](docs/workflows/inbound_single_campaign_matching.md)
- [docs/workflows/latest_campaign_inbound_matching.md](docs/workflows/latest_campaign_inbound_matching.md)
- [docs/debugging/dealer_database.md](docs/debugging/dealer_database.md)
- [docs/testing/admin_test_reset.md](docs/testing/admin_test_reset.md)
- [docs/roadmap.md](docs/roadmap.md)

## Status des Projekts

Der aktuelle Stand ist ein operativ nutzbarer Backend-/Workflow-Prototyp mit klarer Ausrichtung auf:

- stabile Kampagnenorchestrierung
- nachvollziehbare Haendlerkommunikation
- robuste Angebotsauswertung
- maschinenlesbare Entscheidungsdaten fuer n8n

Nicht Ziel dieser Version sind eine vollstaendige BMW-Webautomation, ein allgemeines CRM oder ein generischer Multi-Tenant-Kampagnenmanager.
