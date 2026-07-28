from __future__ import annotations

from datetime import date
from decimal import Decimal
import hashlib
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.entities.vehicle_configuration import VehicleConfiguration
from app.entities.vehicle_configuration_feature import VehicleConfigurationFeature
from app.services.bmw_option_catalog import BMW_MODEL_MAP, BMW_OPTION_MAP, BMW_PAINT_MAP, BMW_UPHOLSTERY_MAP
from app.services.bmw_configuration_resolver import format_resolved_configuration_items, resolve_bmw_configuration
from app.schemas.vehicle_configuration import (
    BMWConfigurationParseResponse,
    DealerRequestPayload,
    ParsedChoice,
    ParsedConfigurationSection,
    ParsedConfigurationSelection,
    ParsedFeatureRequirement,
    ParsedPricing,
    ParsedSource,
    ParsedVehicle,
    ParserMetadata,
)


class BMWConfigurationParserError(ValueError):
    pass


class BMWConfigurationResolutionError(RuntimeError):
    pass


class BMWConfigurationParserService:
    PROVIDER = "BMW"
    VERSION = "1.0"
    ALLOWED_HOSTS = {"configure.bmw.de", "www.bmw.de"}
    REQUEST_TIMEOUT_SECONDS = 5.0
    MAX_REDIRECTS = 3

    def __init__(self, db: Session):
        self.db = db

    def parse_and_store(self, configuration_url: str) -> VehicleConfiguration:
        parsed = self.parse(configuration_url)
        return self._upsert(parsed)

    def parse(self, configuration_url: str) -> BMWConfigurationParseResponse:
        original_url = configuration_url.strip()
        validated_url = self._validate_url(original_url)
        resolved_url = self._resolve_if_needed(validated_url)
        parsed_url = self._validate_url(resolved_url)
        extracted = self._extract(parsed_url, original_url=original_url, resolved_url=resolved_url)
        return self._build_response(extracted)

    def _validate_url(self, configuration_url: str) -> str:
        parsed = urlparse(configuration_url.strip())
        if parsed.scheme not in {"http", "https"}:
            raise BMWConfigurationParserError("Invalid BMW configuration URL.")
        if parsed.netloc.lower() not in self.ALLOWED_HOSTS:
            raise BMWConfigurationParserError("BMW configuration host is not allowed.")
        return configuration_url.strip()

    def _resolve_if_needed(self, configuration_url: str) -> str:
        parsed = urlparse(configuration_url)
        segments = [segment for segment in parsed.path.split("/") if segment]
        if "configid" not in [segment.lower() for segment in segments]:
            return configuration_url
        return self._resolve_short_url(configuration_url)

    def _resolve_short_url(self, configuration_url: str) -> str:
        current_url = configuration_url
        try:
            with httpx.Client(follow_redirects=False, timeout=self.REQUEST_TIMEOUT_SECONDS) as client:
                for _ in range(self.MAX_REDIRECTS):
                    response = client.get(current_url)
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if not location:
                            raise BMWConfigurationResolutionError("BMW configuration redirect did not contain a location.")
                        next_url = httpx.URL(location, base=current_url).human_repr()
                        self._validate_url(next_url)
                        current_url = next_url
                        continue
                    if response.status_code >= 400:
                        raise BMWConfigurationResolutionError("BMW configuration URL could not be resolved.")
                    return str(response.url)
        except httpx.HTTPError:
            return configuration_url
        raise BMWConfigurationResolutionError("BMW configuration redirect chain exceeded the limit.")

    def _extract(self, parsed_url: str, *, original_url: str, resolved_url: str) -> dict[str, Any]:
        parsed = urlparse(parsed_url)
        path_parts = [part for part in parsed.path.split("/") if part]
        lowered_parts = [part.lower() for part in path_parts]
        if "configid" in lowered_parts and "configure" not in lowered_parts:
            configuration_id = self._extract_config_id_from_path(parsed_url) or self._extract_config_id_from_path(original_url)
            warnings = ["BMW short link could not be fully resolved."]
            return {
                "parser": ParserMetadata(provider=self.PROVIDER, version=self.VERSION, status="PARTIALLY_PARSED", warnings=warnings),
                "source": ParsedSource(
                    original_url=original_url,
                    resolved_url=resolved_url,
                    configuration_id=configuration_id,
                    effect_date=None,
                ),
                "vehicle": ParsedVehicle(brand="BMW"),
                "pricing": ParsedPricing(list_price=None, currency="EUR"),
                "configuration": ParsedConfigurationSection(),
                "resolved_configuration": resolve_bmw_configuration(model_code="BMW", option_codes=[]),
                "requirements": [],
            }
        if "configure" not in lowered_parts:
            raise BMWConfigurationParserError("BMW configuration URL is not a supported configure link.")
        configure_index = lowered_parts.index("configure")
        if len(path_parts) <= configure_index + 3:
            raise BMWConfigurationParserError("BMW configuration URL is incomplete.")

        series_code = path_parts[configure_index + 1]
        model_code = path_parts[configure_index + 2]
        raw_codes = [code.strip() for code in path_parts[configure_index + 3].split(",") if code.strip()]
        query = parse_qs(parsed.query)

        ordered_codes = self._deduplicate(raw_codes)
        upholstery_code = next((code for code in ordered_codes if code.startswith("F")), None)
        paint_code = next((code for code in ordered_codes if code.startswith("P")), None)

        option_codes = [code for code in ordered_codes if code not in {upholstery_code, paint_code}]
        configuration_id = (query.get("initialConfigId") or [None])[0] or self._extract_config_id_from_path(original_url)
        effect_date_value = (query.get("effectDate") or [None])[0]
        effect_date = date.fromisoformat(effect_date_value) if effect_date_value else None

        model_info = BMW_MODEL_MAP.get(model_code, {})
        paint_name = BMW_PAINT_MAP.get(paint_code or "")
        upholstery_name = BMW_UPHOLSTERY_MAP.get(upholstery_code or "")

        resolved_configuration = resolve_bmw_configuration(
            model_code=model_code,
            option_codes=ordered_codes,
        )

        warnings: list[str] = []
        options: list[ParsedConfigurationSelection] = []
        features: list[ParsedFeatureRequirement] = []

        features.append(
            ParsedFeatureRequirement(
                feature_key="vehicle.model_name",
                feature_value=model_info.get("model_name") or model_code,
                feature_code=model_code,
                display_label="Variante",
                is_mandatory=True,
            )
        )

        if paint_code:
            features.append(
                ParsedFeatureRequirement(
                    feature_key="configuration.paint",
                    feature_value=paint_name or paint_code,
                    feature_code=paint_code,
                    display_label="Außenfarbe",
                    is_mandatory=False,
                )
            )
        if upholstery_code:
            features.append(
                ParsedFeatureRequirement(
                    feature_key="configuration.upholstery",
                    feature_value=upholstery_name or upholstery_code,
                    feature_code=upholstery_code,
                    display_label="Innenausstattung",
                    is_mandatory=False,
                )
            )

        for option_code in option_codes:
            option_info = BMW_OPTION_MAP.get(option_code)
            if option_info is None:
                warnings.append(f"Unknown option code: {option_code}")
                options.append(
                    ParsedConfigurationSelection(
                        code=option_code,
                        name=None,
                        category="unknown",
                        is_standard=False,
                        is_resolved=False,
                    )
                )
                continue

            options.append(
                ParsedConfigurationSelection(
                    code=option_code,
                    name=option_info["name"],
                    category=option_info["category"],
                    is_standard=False,
                    is_resolved=True,
                )
            )
            features.append(
                ParsedFeatureRequirement(
                    feature_key=f"configuration.option.{option_code.lower()}",
                    feature_value=option_info["name"],
                    feature_code=option_code,
                    display_label=self._display_label_for_category(option_info["category"]),
                    is_mandatory=False,
                )
            )

        status = "PARTIALLY_PARSED" if warnings else "PARSED"
        return {
            "parser": ParserMetadata(provider=self.PROVIDER, version=self.VERSION, status=status, warnings=warnings),
            "source": ParsedSource(
                original_url=original_url,
                resolved_url=resolved_url,
                configuration_id=configuration_id,
                effect_date=effect_date,
            ),
            "vehicle": ParsedVehicle(
                brand="BMW",
                series_code=series_code,
                model_code=model_code,
                model_name=model_info.get("model_name"),
                variant=model_info.get("variant"),
                body=model_info.get("body"),
            ),
            "pricing": ParsedPricing(list_price=None, currency="EUR"),
            "configuration": ParsedConfigurationSection(
                paint=ParsedChoice(code=paint_code, name=paint_name) if paint_code else None,
                upholstery=ParsedChoice(code=upholstery_code, name=upholstery_name) if upholstery_code else None,
                options=options,
            ),
            "resolved_configuration": resolved_configuration,
            "requirements": features,
        }

    def _build_response(self, extracted: dict[str, Any]) -> BMWConfigurationParseResponse:
        vehicle = extracted["vehicle"]
        source = extracted["source"]
        configuration = extracted["configuration"]
        model_name = vehicle.model_name or vehicle.model_code or "BMW Konfiguration"
        subject = f"Anfrage Barkauf – {model_name}"

        lines = format_resolved_configuration_items(extracted["resolved_configuration"])
        lines.append("")
        lines.append("BMW-Konfigurationslink:")
        lines.append(source.original_url)

        return BMWConfigurationParseResponse(
            parser=extracted["parser"],
            source=source,
            vehicle=vehicle,
            pricing=extracted["pricing"],
            configuration=configuration,
            resolved_configuration=extracted["resolved_configuration"],
            requirements=extracted["requirements"],
            dealer_request=DealerRequestPayload(subject=subject, configuration_text="\n".join(lines).strip()),
        )

    def _upsert(self, parsed: BMWConfigurationParseResponse) -> VehicleConfiguration:
        resolved_url_hash = hashlib.sha256(parsed.source.resolved_url.encode("utf-8")).hexdigest()
        statement = select(VehicleConfiguration).where(
            or_(
                (
                    (VehicleConfiguration.provider == self.PROVIDER)
                    & (VehicleConfiguration.configuration_id == parsed.source.configuration_id)
                    & (VehicleConfiguration.effect_date == parsed.source.effect_date)
                    & (VehicleConfiguration.configuration_id.is_not(None))
                ),
                (
                    (VehicleConfiguration.provider == self.PROVIDER)
                    & (VehicleConfiguration.resolved_url_hash == resolved_url_hash)
                ),
            )
        )
        entity = self.db.execute(statement).scalar_one_or_none()
        if entity is None:
            entity = VehicleConfiguration(
                provider=self.PROVIDER,
                configuration_id=parsed.source.configuration_id,
                original_url=parsed.source.original_url,
                resolved_url=parsed.source.resolved_url,
                resolved_url_hash=resolved_url_hash,
                brand=parsed.vehicle.brand,
                series_code=parsed.vehicle.series_code,
                model_code=parsed.vehicle.model_code,
                model_name=parsed.vehicle.model_name,
                variant=parsed.vehicle.variant,
                body=parsed.vehicle.body,
                paint_code=parsed.configuration.paint.code if parsed.configuration.paint else None,
                paint_name=parsed.configuration.paint.name if parsed.configuration.paint else None,
                upholstery_code=parsed.configuration.upholstery.code if parsed.configuration.upholstery else None,
                upholstery_name=parsed.configuration.upholstery.name if parsed.configuration.upholstery else None,
                list_price=parsed.pricing.list_price,
                currency=parsed.pricing.currency,
                effect_date=parsed.source.effect_date,
                parse_status=parsed.parser.status,
                parser_version=parsed.parser.version,
                raw_data={"warnings": parsed.parser.warnings},
                normalized_data=parsed.model_dump(mode="json"),
            )
            self.db.add(entity)
            self.db.flush()
        else:
            entity.configuration_id = parsed.source.configuration_id
            entity.original_url = parsed.source.original_url
            entity.resolved_url = parsed.source.resolved_url
            entity.resolved_url_hash = resolved_url_hash
            entity.brand = parsed.vehicle.brand
            entity.series_code = parsed.vehicle.series_code
            entity.model_code = parsed.vehicle.model_code
            entity.model_name = parsed.vehicle.model_name
            entity.variant = parsed.vehicle.variant
            entity.body = parsed.vehicle.body
            entity.paint_code = parsed.configuration.paint.code if parsed.configuration.paint else None
            entity.paint_name = parsed.configuration.paint.name if parsed.configuration.paint else None
            entity.upholstery_code = parsed.configuration.upholstery.code if parsed.configuration.upholstery else None
            entity.upholstery_name = parsed.configuration.upholstery.name if parsed.configuration.upholstery else None
            entity.list_price = parsed.pricing.list_price
            entity.currency = parsed.pricing.currency
            entity.effect_date = parsed.source.effect_date
            entity.parse_status = parsed.parser.status
            entity.parser_version = parsed.parser.version
            entity.raw_data = {"warnings": parsed.parser.warnings}
            entity.normalized_data = parsed.model_dump(mode="json")
            entity.features.clear()

        entity.features = self._build_feature_entities(parsed, entity.id)
        self.db.flush()
        return entity

    def _build_feature_entities(
        self,
        parsed: BMWConfigurationParseResponse,
        configuration_id: Any,
    ) -> list[VehicleConfigurationFeature]:
        features: list[VehicleConfigurationFeature] = []
        for index, item in enumerate(parsed.requirements):
            features.append(
                VehicleConfigurationFeature(
                    configuration_id=configuration_id,
                    feature_code=item.feature_code,
                    feature_key=item.feature_key,
                    feature_value=item.feature_value,
                    display_label=item.display_label,
                    category=self._category_for_feature(item.feature_key),
                    is_standard=False,
                    is_mandatory=item.is_mandatory,
                    sort_order=index,
                    raw_data=None,
                )
            )
        return features

    @staticmethod
    def _deduplicate(codes: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for code in codes:
            normalized = code.strip().upper()
            if normalized and normalized not in seen:
                result.append(normalized)
                seen.add(normalized)
        return result

    @staticmethod
    def _extract_config_id_from_path(configuration_url: str) -> str | None:
        parsed = urlparse(configuration_url)
        path_parts = [part for part in parsed.path.split("/") if part]
        lowered_parts = [part.lower() for part in path_parts]
        if "configid" not in lowered_parts:
            return None
        index = lowered_parts.index("configid")
        if index + 1 >= len(path_parts):
            return None
        return path_parts[index + 1]

    @staticmethod
    def _display_label_for_category(category: str) -> str:
        mapping = {
            "package": "Paket",
            "wheels": "Räder",
            "driver_assistance": "Fahrerassistenz",
        }
        return mapping.get(category, "Sonderausstattung")

    @staticmethod
    def _category_for_feature(feature_key: str) -> str:
        if feature_key == "vehicle.model_name":
            return "vehicle"
        if "paint" in feature_key:
            return "paint"
        if "upholstery" in feature_key:
            return "upholstery"
        return "option"
