# Single-Campaign Mode

## Goal

The application currently operates in a single-campaign mode. At any time, the valid business state is:

- no campaign
- exactly one campaign

Multiple concurrent campaigns are not allowed.

## Enforcement

The mode is enabled by default through `SINGLE_CAMPAIGN_MODE=true`.

Protection exists on two levels:

- Service layer cleanup via `SingleCampaignService`
- Database constraint on `campaign.singleton_key`

The `campaign` table stores a technical `singleton_key` with the fixed value `1`. A unique constraint prevents the database from persisting more than one campaign row at once.

## Lifecycle

### Campaign creation

When a new campaign is created through the FastAPI service layer, all existing campaigns are removed before the new campaign is persisted.

Dealer master data is preserved.

### Campaign start

When contacts are claimed for a `DRAFT` campaign, the campaign moves to `STARTED`. In the same transactional flow, all other campaigns are deleted.

### Campaign completion

When a campaign is completed, the service again removes all other campaigns before persisting `COMPLETED`.

Completion remains idempotent.

## Deleted dependent data

When an old campaign is removed, campaign-scoped records are removed as well:

- `campaign_configuration`
- `configuration_requirement`
- `campaign_dealer_contact`
- `inbound_email`
- `dealer_offer`
- `dealer_offer_feature`

Dealer master data remains untouched.

## Relevant services

- `app/services/single_campaign_service.py`
- `app/services/campaign_service.py`
- `app/services/campaign_contact_service.py`
- `app/services/campaign_dispatch_service.py`

## Environment

Recommended local settings:

```env
APP_ENV=development
SINGLE_CAMPAIGN_MODE=true
ALLOW_TEST_RESET=true
TEST_RESET_TOKEN=change-me
```
