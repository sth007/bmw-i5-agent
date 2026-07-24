# BMW i5 Agent

FastAPI-, PostgreSQL- und n8n-basiertes Projekt fuer BMW-Kampagnen, Haendlerimport, Angebotsverarbeitung und erste Kampagnenorchestrierung.

## Start

```bash
docker compose up -d --build
docker exec bmw-agent-api alembic upgrade head
docker exec bmw-agent-api pytest
```

Die API ist danach unter `http://localhost:8000` erreichbar, n8n unter `http://localhost:5678`.

## Wichtige API-Endpunkte

### Dealer

- `POST /dealers/import`
- `GET /dealers`
- `GET /dealers/{id}`
- `PATCH /dealers/{id}`
- `DELETE /dealers/{id}`
- `GET /dealers/count`
- `GET /dealers/statistics`

### Campaign Start Workflow

Erste Version des Kampagnenstarts:

- `POST /api/campaigns/start`
- `POST /api/campaigns/from-config`

Beispiel:

```json
{
  "campaign_name": "BMW i5 Touring Juli 2026",
  "config_url": "https://configure.bmw.de/de_DE/configid/chtwyiio",
  "dealer_limit": 3,
  "customer": {
    "name": "Max Mustermann",
    "email": "max.mustermann@example.de",
    "phone": "+49 170 1234567"
  }
}
```

`dealer_limit` ist optional und hat standardmaessig den Wert `3`.

Bei `POST /api/campaigns/from-config` ist `customer` erforderlich. Der Endpunkt erzeugt nur Vorschauen und versendet keine E-Mails.

Diese Version:

- erzeugt eine Kampagne
- speichert `config_url`
- extrahiert und speichert `config_id`
- waehlt die ersten veroeffentlichten Haendler mit E-Mail
- erzeugt E-Mail-Vorschauen auf Basis versionierter Jinja2-Templates
- liest die BMW-Konfiguration noch nicht aus, sondern setzt nur den Link in das Template ein

Falls keine geeigneten Haendler gefunden werden, wird die Kampagne trotzdem angelegt. Die Response enthaelt dann leere `dealers`- und `email_previews`-Arrays sowie eine Warnung.

Beispiel fuer n8n:

```json
{
  "campaign_name": "Neue BMW Kampagne",
  "config_url": "{{$json.config_url}}",
  "dealer_limit": 3,
  "customer": {
    "name": "Max Mustermann",
    "email": "max.mustermann@example.de",
    "phone": ""
  }
}
```

Noch nicht enthalten:

- automatisches Auslesen der BMW-Webseite
- SMTP-Versand
- PDF-Download
- KI-Auswertung

## n8n

n8n dient als Orchestrierung und Debug-Oberflaeche.

Vorhandene Workflows:

- `n8n/BMW – Incoming Dealer Offers.json`
- `n8n/BMW – Dealer Database Debug.json`

Hinweise zur PostgreSQL-Debugging-Strecke:

- siehe [docs/debugging/dealer_database.md](docs/debugging/dealer_database.md)

## Tests

Die Test-Suite deckt unter anderem ab:

- Dealer Import und Debug-Endpunkte
- Kampagnenstart und Config-ID-Extraktion
- Dealer-Auswahl und E-Mail-Preview
- Angebotsvergleich und Ranking
- Alembic Upgrade/Downgrade
