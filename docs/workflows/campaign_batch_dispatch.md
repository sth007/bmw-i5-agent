# Campaign Batch Dispatch

Workflow A should process campaign contacts in batches instead of sending all dealer requests at once.

Recommended flow:

1. `POST /api/campaigns/from-config`
2. `POST /api/campaigns/{campaign_id}/contacts/claim` with `limit`
3. Split claimed contacts
4. Send Gmail messages
5. `POST /api/campaign-contacts/{contact_id}/sent`
6. `GET /api/campaigns/{campaign_id}/dispatch-status`

Important:

- Only contacts returned by `/contacts/claim` may be sent.
- `pending` contacts are still sendable.
- `reserved`, `sent`, `replied`, `offer_extracted`, `needs_review`, `send_state_unknown`, and `skipped` must not be claimed again.
- Batch size is controlled by the request body field `limit`.

Example claim request:

```json
{
  "limit": 30,
  "reservation_owner": "n8n-execution-12345",
  "test_mode": true,
  "test_recipient": "zaour.ludwigsburger@gmail.com"
}
```
