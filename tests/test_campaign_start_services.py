from app.entities.dealer import Dealer
from app.services.campaign_service import CampaignService
from app.services.dealer_selection_service import DealerSelectionService
from app.services.email_template_service import DEFAULT_CUSTOMER_NAME, EmailTemplateService


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


def test_email_template_service_renders_subject_and_body() -> None:
    preview = EmailTemplateService().render_campaign_request(
        dealer_id=143,
        campaign_name="BMW i5 Touring Juli 2026",
        config_url="https://configure.bmw.de/de_DE/configid/chtwyiio",
        dealer_name="BMW AG Niederlassung Stuttgart",
        dealer_email="bmw-stuttgart@bmw.de",
        customer_name="Max Mustermann",
        customer_email="max.mustermann@example.de",
        customer_phone=None,
    )

    assert preview.dealer_id == 143
    assert preview.dealer_name == "BMW AG Niederlassung Stuttgart"
    assert preview.to == "bmw-stuttgart@bmw.de"
    assert preview.subject == "Anfrage zu meiner BMW Wunschkonfiguration"
    assert "https://configure.bmw.de/de_DE/configid/chtwyiio" in preview.body
    assert "Max Mustermann" in preview.body
    assert "BMW AG Niederlassung Stuttgart" in preview.body
    assert "None" not in preview.body
    assert "undefined" not in preview.body
    assert "\n\n" in preview.body


def test_email_template_service_omits_missing_optional_customer_fields() -> None:
    preview = EmailTemplateService().render_campaign_request(
        dealer_id=1,
        campaign_name="BMW i5 Touring Juli 2026",
        config_url="https://configure.bmw.de/de_DE/configid/chtwyiio",
        dealer_name=None,
        dealer_email="dealer@example.com",
        customer_name="Max Mustermann",
        customer_email=None,
        customer_phone="  ",
    )

    assert "None" not in preview.body
    assert "null" not in preview.body
    assert "undefined" not in preview.body
    assert "Sehr geehrte Damen und Herren," in preview.body


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
    assert response.email_previews[0].dealer_name == "A"


def test_start_campaign_uses_default_customer_name_for_compatibility(db_session) -> None:
    dealers = [
        Dealer(bmw_dealer_id="dealer-001", name="A", email="a@example.com", is_published=True),
    ]
    db_session.add_all(dealers)
    db_session.commit()

    response = CampaignService(db_session).start_campaign(
        campaign_name="BMW i5 Touring Juli 2026",
        config_url="https://configure.bmw.de/de_DE/configid/chtwyiio",
        dealer_limit=1,
    )

    assert DEFAULT_CUSTOMER_NAME in response.email_previews[0].body


def test_start_campaign_returns_warning_when_no_eligible_dealers_exist(db_session) -> None:
    db_session.add(
        Dealer(bmw_dealer_id="dealer-001", name="A", email=None, is_published=True),
    )
    db_session.commit()

    response = CampaignService(db_session).start_campaign(
        campaign_name="BMW i5 Touring Juli 2026",
        config_url="https://configure.bmw.de/de_DE/configid/chtwyiio",
        dealer_limit=3,
    )

    assert response.dealers == []
    assert response.email_previews == []
    assert response.warnings == ["No eligible dealers with a valid email address were found."]
