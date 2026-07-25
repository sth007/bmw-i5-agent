# Latest Campaign Inbound Matching

Workflow B should resolve the most recent relevant campaign before registering an inbound message.

Relevant campaign statuses:

- `STARTED`
- `COMPLETED`

Ignored:

- `DRAFT`
- `CANCELLED`

Recommended flow:

1. `GET /api/campaigns/latest-relevant`
2. add `campaign_id_hint` in the normalized inbound payload
3. `POST /api/inbound-emails`
4. `POST /api/inbound-emails/{inbound_email_id}/extract-offer`

Example hint:

```json
{
  "campaign_id_hint": "dc19143b-b086-4d26-a77d-ce1e02937007"
}
```

Within the hinted campaign, dealer matching still follows this order:

1. `provider_thread_id`
2. `in_reply_to`
3. `references`
4. campaign token in the subject
5. `sender_email`
6. review case

If the campaign is known but the dealer is not uniquely identified, the inbound email is stored with:

- `campaign_id` set
- `dealer_id = null`
- `matching_status = NEEDS_DEALER_ASSIGNMENT`
- `processing_status = NEEDS_REVIEW`
