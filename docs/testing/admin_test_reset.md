# Admin Test Reset

## Purpose

For repeatable local and n8n-driven end-to-end tests, the API exposes a guarded reset endpoint in development and test environments.

## Endpoints

### Status

```http
GET /api/admin/reset-status
X-Reset-Token: <token>
```

### Reset

```http
POST /api/admin/reset-test-state
X-Reset-Token: <token>
Content-Type: application/json
```

## Availability

The endpoint is available only when both conditions are true:

- `APP_ENV` is `development` or `test`
- `ALLOW_TEST_RESET=true`

Requests with a wrong or missing token return `403 Forbidden`.

Requests in production return `404 Not Found`.

## Environment variables

```env
APP_ENV=development
ALLOW_TEST_RESET=true
TEST_RESET_TOKEN=change-me
```

## Reset scopes

### `campaign_data`

```json
{
  "scope": "campaign_data"
}
```

Deletes campaign-scoped data while keeping dealer master data.

### `all_application_data`

```json
{
  "scope": "all_application_data",
  "confirm": "RESET"
}
```

Deletes campaign-scoped data and imported dealer data. The explicit confirmation is mandatory.

## n8n example

Use an HTTP Request node:

- Method: `POST`
- URL: `http://bmw-agent-api:8000/api/admin/reset-test-state`
- Header: `X-Reset-Token: {{$env.TEST_RESET_TOKEN}}`

Body for a normal reset:

```javascript
={{
  scope: 'campaign_data'
}}
```

Body for a full test-data reset:

```javascript
={{
  scope: 'all_application_data',
  confirm: 'RESET'
}}
```

## Notes

- The reset is intended for local development and automated testing only.
- Dealer master data survives `campaign_data` resets.
- The endpoint does not drop schemas or rerun migrations.
