# BMW i5 Agent

Python-Startpunkt fuer ein Agent-Projekt rund um den BMW i5.

Der aktuelle Stand des Repositories ist ein leichtes Projektgeruest mit Python-Abhaengigkeiten, aber noch ohne implementierte Anwendungslogik in `app/main.py`.

## Projektstruktur

```text
.
├── app/
│   └── main.py
├── data/
├── docs/
├── scripts/
├── tests/
└── requirements.txt
```

## Voraussetzungen

- Python 3.11 oder neuer
- `pip`
- optional: virtuelles Environment mit `.venv`

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Projekt starten

`app/main.py` ist aktuell leer. Sobald die Implementierung vorhanden ist, kann das Projekt voraussichtlich so gestartet werden:

```bash
python3 app/main.py
```

## Abhaengigkeiten

Die bisher eingetragenen Pakete deuten auf ein Python-Projekt mit OpenAI-API-Nutzung hin:

- `openai`
- `python-dotenv`
- `httpx`
- `pydantic`
- `requests`

## Geplanter Aufbau

- `app/` enthaelt die eigentliche Anwendungslogik
- `data/` ist fuer lokale Daten oder Beispielinputs vorgesehen
- `docs/` kann technische Dokumentation aufnehmen
- `scripts/` ist fuer Hilfsskripte gedacht
- `tests/` ist fuer automatisierte Tests reserviert

## Environment-Variablen

Falls das Projekt spaeter mit der OpenAI-API arbeitet, ist typischerweise mindestens diese Variable noetig:

```bash
export OPENAI_API_KEY="..."
```

Alternativ kann eine `.env`-Datei verwendet werden. Sie ist bereits in `.gitignore` ausgeschlossen.

## Status

Stand 22. Juli 2026:

- Projektgeruest vorhanden
- Python-Abhaengigkeiten definiert
- keine implementierte Laufzeitlogik
- keine Tests vorhanden

## Naechste sinnvolle Schritte

1. Einstiegspunkt in `app/main.py` implementieren.
2. Konfiguration ueber `.env` oder Settings-Modul definieren.
3. Testbasis unter `tests/` anlegen.
4. Dokumentation in `docs/` ergaenzen, sobald Use-Cases klar sind.
