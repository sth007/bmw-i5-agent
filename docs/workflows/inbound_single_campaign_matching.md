# Inbound Matching In Single-Campaign Mode

## Overview

Inbound email registration is handled by `POST /api/inbound-emails`.

In single-campaign mode, the API no longer depends on n8n to pass a campaign for every inbound message. If exactly one relevant campaign exists, the API assigns it automatically.

## Matching order

### 1. Explicit campaign hint

If `campaign_id_hint` is present, the API loads the campaign and accepts it only when the status is:

- `STARTED`
- `COMPLETED`

Invalid hints return a client error.

### 2. Single-campaign fallback

If no valid hint exists, the API loads the only campaign in the system.

If that campaign is `STARTED` or `COMPLETED`, it becomes the effective campaign context for matching.

If no campaign exists, the inbound email is stored with:

- `campaign_id = null`
- `matching_status = NO_CAMPAIGN`
- `processing_status = NEEDS_REVIEW`

If multiple campaigns somehow exist despite the singleton protection, the API returns a controlled conflict state.

## Dealer matching inside the selected campaign

After the campaign has been determined, dealer matching runs in this order:

1. `provider_thread_id`
2. `in_reply_to`
3. `references`
4. campaign token in subject
5. `sender_email`

If the campaign is known but no dealer can be resolved, the email is stored with:

- `matching_status = NEEDS_DEALER_ASSIGNMENT`
- `processing_status = NEEDS_REVIEW`

`UNMATCHED` is not used in that case.

## Response behavior

If a campaign and dealer were matched successfully:

- `processing_status = REGISTERED`
- `can_extract = true`

If campaign resolution succeeded but dealer resolution did not:

- `processing_status = NEEDS_REVIEW`
- `can_extract = false`

## Related endpoints

- `POST /api/inbound-emails`
- `GET /api/inbound-emails/{id}/debug-match`
- `POST /api/inbound-emails/{id}/extract-offer`
- `GET /api/campaigns/latest-relevant`
