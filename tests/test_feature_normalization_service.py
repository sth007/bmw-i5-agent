from app.services.feature_normalization_service import FeatureNormalizationService


def test_normalizes_feature_key_and_value() -> None:
    service = FeatureNormalizationService()

    normalized_key, normalized_value = service.normalize_feature(
        "M Sportpaket Pro",
        " Ja ",
    )

    assert normalized_key == "m_sportpaket_pro"
    assert normalized_value == "true"


def test_normalizes_free_text_without_bool_mapping() -> None:
    service = FeatureNormalizationService()

    assert service.normalize_value(" Sophisto Grau ") == "sophisto grau"
