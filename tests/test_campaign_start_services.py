from app.entities.dealer import Dealer
from app.services.campaign_service import CampaignService
from app.services.dealer_selection_service import DealerSelectionService
from app.services.email_preview_service import EMAIL_SUBJECT, EmailPreviewService


def test_extract_config_id_from_bmw_config_url(db_session) -> None:
    service = CampaignService(db_session)

    assert service.extract_config_id("https://configure.bmw.de/de_DE/configid/chtwyiio") == "chtwyiio"


def test_extract_config_id_rejects_invalid_bmw_url(db_session) -> None:
    service = CampaignService(db_session)

    assert service.extract_config_id("https://example.com/configid/chtwyiio") is None


def test_dealer_selection_respects_limit_and_publication(db_session) -> None:
    dealers = [
        Dealer(bmw_dealer_id="dealer-001", name="A", email="a@example.com", is_published=True),
        Dealer(bmw_dealer_id="dealer-002", name="B", email="b@example.com", is_published=True),
        Dealer(bmw_dealer_id="dealer-003", name="C", email="c@example.com", is_published=False),
        Dealer(bmw_dealer_id="dealer-004", name="D", email=None, is_published=True),
    ]
    db_session.add_all(dealers)
    db_session.commit()

    selected = DealerSelectionService(db_session).select_initial_dealers(2)

    assert [dealer.bmw_dealer_id for dealer in selected] == ["dealer-001", "dealer-002"]


def test_email_preview_generation_uses_template(db_session) -> None:
    dealer = Dealer(
        id=143,
        bmw_dealer_id="dealer-143",
        name="BMW AG Niederlassung Stuttgart",
        city="Stuttgart",
        email="bmw-stuttgart@bmw.de",
        is_published=True,
    )

    preview = EmailPreviewService().build_preview(
        dealer,
        "https://configure.bmw.de/de_DE/configid/chtwyiio",
    )

    assert preview.dealer_id == 143
    assert preview.to == "bmw-stuttgart@bmw.de"
    assert preview.subject == EMAIL_SUBJECT
    assert "chtwyiio" in preview.body


def test_start_campaign_persists_campaign_and_returns_previews(db_session) -> None:
    dealers = [
        Dealer(bmw_dealer_id="dealer-001", name="A", email="a@example.com", is_published=True),
        Dealer(bmw_dealer_id="dealer-002", name="B", email="b@example.com", is_published=True),
        Dealer(bmw_dealer_id="dealer-003", name="C", email="c@example.com", is_published=True),
    ]
    db_session.add_all(dealers)
    db_session.commit()

    response = CampaignService(db_session).start_campaign(
        campaign_name="BMW i5 Touring Juli 2026",
        config_url="https://configure.bmw.de/de_DE/configid/chtwyiio",
        dealer_limit=2,
    )

    assert response.config_id == "chtwyiio"
    assert response.status == "DRAFT"
    assert len(response.dealers) == 2
    assert len(response.email_previews) == 2
