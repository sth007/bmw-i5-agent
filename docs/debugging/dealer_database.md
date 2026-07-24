# Dealer Database Debugging

## Überblick

- Stand der Analyse: 24. Juli 2026
- PostgreSQL-Tabelle für Händler: `public.dealer`
- Primärschlüssel: `id`
- Eindeutiger Fachschlüssel: `bmw_dealer_id`
- Soft-Delete: nicht vorhanden
- Aktiv-Flag: `is_published`

## Datenbankschema

Die Händlertabelle heißt `dealer`.

Wichtige Constraints:

- `PRIMARY KEY (id)`
- `UNIQUE (bmw_dealer_id)`
- zusätzlicher eindeutiger Index: `ix_dealer_bmw_dealer_id`

Wichtige Felder:

- `id`: technischer Primärschlüssel
- `bmw_dealer_id`: eindeutige BMW-Händler-ID
- `name`: Händlername
- `city`: Ort
- `email`, `phone`: generische Kontaktinformationen
- `new_car_email`, `new_car_phone`: Kontakt für Neuwagen
- `used_car_email`, `used_car_phone`: Kontakt für Gebrauchtwagen
- `new_car_sales`, `used_car_sales`: Verkaufskanäle
- `is_published`: aktiver/sichtbarer Händler
- `last_sync`: Zeitstempel des letzten Imports
- `created_at`, `updated_at`: technische Zeitstempel

Beim Import über `POST /dealers/import` werden derzeit befüllt:

- `bmw_dealer_id`
- `distribution_partner_id`
- `outlet_id`
- `name`
- `street`
- `postal_code`
- `city`
- `country`
- `latitude`
- `longitude`
- `homepage`
- `email`
- `phone`
- `new_car_email`
- `new_car_phone`
- `used_car_email`
- `used_car_phone`
- `new_car_sales`
- `used_car_sales`
- `is_published`
- `last_sync`

`created_at` und `updated_at` werden durch SQLAlchemy gesetzt. `last_sync` wird im Import-Service auf die aktuelle UTC-Zeit gesetzt.

## SQL-Abfragen für n8n

### 1. Tabellenübersicht

```sql
SELECT
    table_schema,
    table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

### 2. Spaltenübersicht der Händlertabelle

```sql
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'dealer'
ORDER BY ordinal_position;
```

### 3. Constraints der Händlertabelle

```sql
SELECT
    tc.constraint_name,
    tc.constraint_type,
    kcu.column_name
FROM information_schema.table_constraints AS tc
LEFT JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
   AND tc.table_schema = kcu.table_schema
WHERE tc.table_schema = 'public'
  AND tc.table_name = 'dealer'
ORDER BY tc.constraint_type, tc.constraint_name, kcu.ordinal_position;
```

### 4. Anzahl der Händler

```sql
SELECT COUNT(*) AS dealer_count
FROM public.dealer;
```

### 5. Händlerübersicht

```sql
SELECT
    *
FROM public.dealer
ORDER BY updated_at DESC NULLS LAST,
         created_at DESC NULLS LAST,
         id DESC;
```

### 6. Letzte 20 importierte Händler

```sql
SELECT
    id,
    bmw_dealer_id,
    name,
    city,
    email,
    phone,
    is_published,
    last_sync,
    created_at,
    updated_at
FROM public.dealer
ORDER BY updated_at DESC NULLS LAST,
         created_at DESC NULLS LAST,
         id DESC
LIMIT 20;
```

### 7. Dubletten nach BMW-Händler-ID

Durch den Unique-Constraint sollten hier normalerweise keine Treffer entstehen.

```sql
SELECT
    bmw_dealer_id,
    COUNT(*) AS duplicate_count
FROM public.dealer
GROUP BY bmw_dealer_id
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC,
         bmw_dealer_id;
```

Nur die Anzahl der Dublettengruppen:

```sql
SELECT COUNT(*) AS duplicate_bmw_dealer_id_groups
FROM (
    SELECT bmw_dealer_id
    FROM public.dealer
    GROUP BY bmw_dealer_id
    HAVING COUNT(*) > 1
) AS duplicate_groups;
```

### 8. Anzahl unterschiedlicher Städte

```sql
SELECT COUNT(DISTINCT city) AS distinct_city_count
FROM public.dealer
WHERE city IS NOT NULL
  AND BTRIM(city) <> '';
```

### 9. Anzahl aktiver Händler

```sql
SELECT COUNT(*) AS active_dealer_count
FROM public.dealer
WHERE is_published = TRUE;
```

### 10. Fehlende Pflichtfelder

Händler ohne Name:

```sql
SELECT *
FROM public.dealer
WHERE name IS NULL
   OR BTRIM(name) = '';
```

Händler ohne Ort:

```sql
SELECT *
FROM public.dealer
WHERE city IS NULL
   OR BTRIM(city) = '';
```

Händler ohne BMW-ID:

```sql
SELECT *
FROM public.dealer
WHERE bmw_dealer_id IS NULL
   OR BTRIM(bmw_dealer_id) = '';
```

Händler ohne E-Mail:

```sql
SELECT *
FROM public.dealer
WHERE email IS NULL
   OR BTRIM(email) = '';
```

Händler ohne Telefonnummer:

```sql
SELECT *
FROM public.dealer
WHERE phone IS NULL
   OR BTRIM(phone) = '';
```

Fehlerhafte Datensätze für Debug-Statistik:

```sql
SELECT *
FROM public.dealer
WHERE name IS NULL
   OR BTRIM(name) = ''
   OR city IS NULL
   OR BTRIM(city) = ''
   OR bmw_dealer_id IS NULL
   OR BTRIM(bmw_dealer_id) = ''
   OR (
       (email IS NULL OR BTRIM(email) = '')
       AND (phone IS NULL OR BTRIM(phone) = '')
   );
```

Nur die Anzahl:

```sql
SELECT COUNT(*) AS invalid_record_count
FROM public.dealer
WHERE name IS NULL
   OR BTRIM(name) = ''
   OR city IS NULL
   OR BTRIM(city) = ''
   OR bmw_dealer_id IS NULL
   OR BTRIM(bmw_dealer_id) = ''
   OR (
       (email IS NULL OR BTRIM(email) = '')
       AND (phone IS NULL OR BTRIM(phone) = '')
   );
```

## Beispielausgaben

Beispiel Dealer Count:

```json
[
  {
    "dealer_count": "128"
  }
]
```

Beispiel Dealer Statistics:

```json
{
  "dealer_count": 128,
  "active_dealer_count": 121,
  "inactive_dealer_count": 7,
  "distinct_city_count": 84,
  "duplicate_bmw_dealer_id_count": 0,
  "invalid_record_count": 5
}
```

## Verwendung in n8n

- Verwende im PostgreSQL-Node die Datenbank aus `docker-compose.yml`.
- Innerhalb des Docker-Netzwerks ist der Host `postgres`.
- Port: `5432`
- Datenbankname: Wert aus `${POSTGRES_DB}`
- Benutzer: Wert aus `${POSTGRES_USER}`
- Passwort: Wert aus `${POSTGRES_PASSWORD}`

Empfohlene Schritte in n8n:

1. PostgreSQL-Credentials mit Host `postgres` anlegen.
2. Für jede Abfrage einen eigenen PostgreSQL-Node mit `Execute Query` verwenden.
3. Ergebnisse in einem `Code`-Node zu einer Debug-Zusammenfassung aggregieren.
4. Für manuelle Prüfung den Workflow [BMW – Dealer Database Debug.json](/Users/zaour/Documents/GitHub/bmw-i5-agent/n8n/BMW%20%E2%80%93%20Dealer%20Database%20Debug.json) importieren.
