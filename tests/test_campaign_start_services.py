from app.entities.dealer import Dealer
from app.services.campaign_service import CampaignService
from app.services.dealer_selection_service import DealerSelectionService
from app.services.email_template_service import DEFAULT_CUSTOMER_NAME, EmailTemplateService
from app.schemas.campaign import CampaignCustomerInput, CampaignFromPublicConfigRequest


def test_extract_config_id_from_bmw_config_url(db_session) -> None:
    service = CampaignService(db_session)

    assert service.extract_config_id("https://configure.bmw.de/de_DE/configid/chtwyiio") == "chtwyiio"


def test_extract_config_id_from_full_bmw_config_url_query(db_session) -> None:
    service = CampaignService(db_session)

    assert (
        service.extract_config_id(
            "https://configure.bmw.de/de_DE/configure/G61E/51HH/FKSFU,P0A90/SE000001"
            "?initialConfigId=chtwyiio&effectDate=2026-09-08"
        )
        == "chtwyiio"
    )


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
        configuration_items=[
            "Variante: BMW i5 xDrive40 Touring",
            "Außenfarbe: Sophistograu Brillanteffekt metallic",
        ],
    )

    assert preview.dealer_id == 143
    assert preview.dealer_name == "BMW AG Niederlassung Stuttgart"
    assert preview.to == "bmw-stuttgart@bmw.de"
    assert preview.subject == "Anfrage zu meiner BMW Wunschkonfiguration"
    assert "https://configure.bmw.de/de_DE/configid/chtwyiio" in preview.body
    assert "Variante: BMW i5 xDrive40 Touring" in preview.body
    assert "Außenfarbe: Sophistograu Brillanteffekt metallic" in preview.body
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


def test_email_template_service_uses_custom_body_template_when_provided() -> None:
    preview = EmailTemplateService().render_campaign_request(
        dealer_id=1,
        campaign_name="BMW i5 Touring Juli 2026",
        config_url="https://configure.bmw.de/de_DE/configid/chtwyiio",
        dealer_name="BMW AG Niederlassung Stuttgart",
        dealer_email="dealer@example.com",
        customer_name="Max Mustermann",
        customer_email="max.mustermann@example.de",
        configuration_items=[
            "Variante: BMW i5 xDrive40 Touring",
            "Außenfarbe: Sophistograu Brillanteffekt metallic",
        ],
        body_template=(
            "Hallo {{ dealer_name }},\n"
            "Link: {{ config_url }}\n"
            "{% for item in configuration_items %}* {{ item }}\n{% endfor %}"
        ),
    )

    assert preview.body.startswith("Hallo BMW AG Niederlassung Stuttgart,")
    assert "* Variante: BMW i5 xDrive40 Touring" in preview.body
    assert "Meine gewünschte Fahrzeugkonfiguration" not in preview.body


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


def test_dealer_selection_returns_three_dealers_from_large_dataset(db_session) -> None:
    dealers = [
        Dealer(
            bmw_dealer_id=f"dealer-{index:03d}",
            name=f"Dealer {index}",
            email=f"dealer{index}@example.com",
            is_published=True,
        )
        for index in range(1, 160)
    ]
    db_session.add_all(dealers)
    db_session.commit()

    selected = DealerSelectionService(db_session).select_for_campaign(3)

    assert len(selected) == 3
    assert [dealer.id for dealer in selected] == [1, 2, 3]


def test_campaign_service_uses_exact_repository_selection(db_session) -> None:
    dealers = [
        Dealer(
            bmw_dealer_id=f"bmw-real-{index:03d}",
            name=f"BMW Niederlassung {index}",
            city=f"City {index}",
            email=f"haendler{index}@bmw.de",
            is_published=True,
        )
        for index in range(1, 5)
    ]
    db_session.add_all(dealers)
    db_session.commit()

    dealer_selection_service = DealerSelectionService(db_session)
    selected = dealer_selection_service.select_for_campaign(3)

    response = CampaignService(db_session).create_from_config(
        campaign_name="BMW i5 Touring Juli 2026",
        config_url="https://configure.bmw.de/de_DE/configid/chtwyiio",
        dealer_limit=3,
        customer=CampaignCustomerInput(name="Max Mustermann"),
    )

    assert [dealer.dealer_id for dealer in response.dealers] == [dealer.id for dealer in selected]


def test_create_from_config_uses_custom_email_body_template(db_session) -> None:
    dealers = [
        Dealer(bmw_dealer_id="dealer-001", name="A", email="a@example.com", is_published=True),
    ]
    db_session.add_all(dealers)
    db_session.commit()

    response = CampaignService(db_session).create_from_config(
        campaign_name="BMW i5 Touring Juli 2026",
        config_url="https://configure.bmw.de/de_DE/configid/chtwyiio",
        dealer_limit=1,
        customer=CampaignCustomerInput(name="Max Mustermann"),
        email_body_template=(
            "Custom intro\n"
            "Dealer: {{ dealer_name }}\n"
            "{% for item in configuration_items %}- {{ item }}\n{% endfor %}"
        ),
    )

    assert response.email_previews[0].body.startswith("Custom intro")
    assert "Dealer: A" in response.email_previews[0].body
    assert "Meine gewünschte Fahrzeugkonfiguration" not in response.email_previews[0].body


def test_create_from_public_config_builds_configuration_from_codes(db_session) -> None:
    dealers = [
        Dealer(bmw_dealer_id="dealer-001", name="A", email="a@example.com", is_published=True),
        Dealer(bmw_dealer_id="dealer-002", name="B", email="b@example.com", is_published=True),
    ]
    db_session.add_all(dealers)
    db_session.commit()

    response = CampaignService(db_session).create_from_public_config(
        CampaignFromPublicConfigRequest.model_validate(
            {
                "campaign_name": "BMW i5 Zaour",
                "dealer_limit": 2,
                "customer": {
                    "name": "Zaour Assadov",
                    "email": "bmw.agent@assadov.de",
                    "phone": "+49 176 99791071",
                },
                "notes": "Nur Barkauf-Angebote relevant.",
                "maximum_target_price": 57000,
                "payment_preference": "cash",
                "public_configuration": {
                    "config_id": "chtwyiio",
                    "effect_date": "2026-09-08",
                    "model_code": "51HH",
                    "option_codes": ["FKSFU", "P0A90", "S0337"],
                    "accessories": {"SE000001": {"accessoryId": "SE000001", "quantity": 1}},
                    "original_configuration_url": "https://configure.bmw.de/de_DE/configid/chtwyiio",
                },
            }
        )
    )

    campaign = CampaignService(db_session).get_campaign(response.campaign_id)

    assert response.config_id == "chtwyiio"
    assert campaign is not None
    assert campaign.configuration is not None
    assert campaign.configuration.model == "BMW i5 xDrive40 Touring"
    assert campaign.configuration.variant == "xDrive40"
    assert [item.feature_key for item in campaign.configuration.requirements] == [
        "vehicle.model_name",
        "configuration.paint",
        "configuration.upholstery",
        "configuration.option.s0337",
        "configuration.accessory.se000001",
    ]
