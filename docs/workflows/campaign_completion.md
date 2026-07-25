# Campaign Completion

Campaign completion is separate from offer processing.

`COMPLETED` means:

- all intended dealer contacts have been processed for outbound dispatch
- no further automatic dispatch batch is pending
- inbound replies and offer extraction may still continue afterward

API endpoint:

```http
POST /api/campaigns/{campaign_id}/complete
```

Optional body:

```json
{
  "completed_by": "n8n",
  "n8n_execution_id": "12345"
}
```

Completion is blocked while any of these statuses still exist:

- `PENDING`
- `RESERVED`
- `SEND_FAILED`
- `SEND_STATE_UNKNOWN`

Recommended n8n pattern:

1. call `GET /api/campaigns/{campaign_id}/dispatch-status`
2. if `has_more_sendable_contacts` is `false` and `can_complete` is `true`
3. call `POST /api/campaigns/{campaign_id}/complete`

The completion endpoint is idempotent. Repeating the request for an already completed campaign returns success again.
