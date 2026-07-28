# BMW Configuration Pipeline

## Zielbild

Die BMW-Konfiguration wird strikt datenorientiert verarbeitet:

1. BMW API oder BMW-Konfigurator-URL liefern Rohdaten.
2. Der Parser erzeugt `resolved_configuration`.
3. Die Kampagne speichert diese strukturierte Konfiguration dauerhaft.
4. `configuration_items` werden nur aus `resolved_configuration` abgeleitet.
5. Das Jinja-Template rendert daraus den finalen E-Mail-Text.

Der E-Mail-Text ist damit reine Ausgabe und keine Datenquelle mehr.

## Persistenz

`campaign_configuration.resolved_configuration` enthaelt die fachlich aufgeloeste Struktur:

```json
{
  "model": {"code": "51HH", "name": "BMW i5 xDrive40 Touring"},
  "color": {"code": "P0A90", "name": "Sophistograu Brillanteffekt metallic"},
  "interior": {"code": "FKSFU", "name": "Veganza perforiert und gesteppt | Rauchweiß"},
  "packages": [{"code": "S0337", "name": "M Sportpaket"}],
  "wheels": [{"code": "S03G9", "name": "19 Zoll M Leichtmetallräder Doppelspeiche 935 M"}],
  "driver_assistance": [{"code": "S05AS", "name": "Driving Assistant"}],
  "other_options": [],
  "accessories": [],
  "unknown_codes": ["SE000001"]
}
```

## Regeln fuer BMW-Codes

- Bekannte Codes werden nach Kategorie aufgeloest.
- Unbekannte Codes werden nur in `unknown_codes` gespeichert.
- Unbekannte Codes erscheinen nie in `configuration_items`.
- Unbekannte Codes erscheinen nie im gerenderten E-Mail-Body.

## Auswirkungen auf Templates

Template-Aenderungen brechen die Datenpipeline nicht mehr, weil:

- das Template nur `configuration_items` konsumiert
- `configuration_items` aus strukturierter Persistenz kommen
- kein spaeterer Regex-Schritt mehr den Mailtext analysieren muss

## Bewertung der `body`-Persistenz

Ein Kampagnen-Body muss nicht dauerhaft als Primärdatenquelle gespeichert werden.

Der aktuelle Stand im Backend ist:

- gespeichert werden Template, Kunde, Haendlerbezug und strukturierte Konfiguration
- der finale Body wird beim Claim/Versand gerendert
- pro `campaign_dealer_contact` bleibt `rendered_body` als Versand-/Audit-Snapshot sinnvoll

Damit ist die fachliche Quelle bereits datenorientiert; nur der tatsaechlich versendete Kontaktinhalt bleibt als Nachweis erhalten.

## n8n-Folgen

Nach diesem Refactoring koennen im outbound-orientierten Workflow entfernt werden:

- Node `Vehicle equipment`
- alle Regex- oder Text-Parsing-Schritte, die den bereits gerenderten E-Mail-Body analysieren
- alle Regeln, die rohe BMW-Codes wie `S0230` oder `SE000001` aus dem Body extrahieren oder filtern

Stattdessen sollte n8n nur noch:

- strukturierte API-Daten verwenden
- den vom Backend gelieferten gerenderten Body versenden
- Versandstatus zurueckmelden
