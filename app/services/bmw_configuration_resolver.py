from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.schemas.bmw_configuration import ResolvedBMWConfiguration, ResolvedConfigurationEntry
from app.services.bmw_option_catalog import (
    BMW_ACCESSORY_MAP,
    BMW_MODEL_MAP,
    BMW_OPTION_MAP,
    BMW_PAINT_MAP,
    BMW_UPHOLSTERY_MAP,
)


CATEGORY_TO_BUCKET = {
    "package": "packages",
    "wheels": "wheels",
    "driver_assistance": "driver_assistance",
}


def resolve_bmw_configuration(
    *,
    model_code: str,
    option_codes: list[str],
    accessories: Mapping[str, Any] | None = None,
) -> ResolvedBMWConfiguration:
    normalized_model_code = model_code.strip().upper()
    model_info = BMW_MODEL_MAP.get(normalized_model_code, {})
    resolved = ResolvedBMWConfiguration(
        model=ResolvedConfigurationEntry(
            code=normalized_model_code,
            name=model_info.get("model_name") or normalized_model_code,
        )
    )

    normalized_codes = _deduplicate_codes(option_codes)
    for code in normalized_codes:
        if code.startswith("P"):
            paint_name = BMW_PAINT_MAP.get(code)
            if paint_name is None:
                resolved.unknown_codes.append(code)
            else:
                resolved.color = ResolvedConfigurationEntry(code=code, name=paint_name)
            continue

        if code.startswith("F"):
            interior_name = BMW_UPHOLSTERY_MAP.get(code)
            if interior_name is None:
                resolved.unknown_codes.append(code)
            else:
                resolved.interior = ResolvedConfigurationEntry(code=code, name=interior_name)
            continue

        option_info = BMW_OPTION_MAP.get(code)
        if option_info is None:
            resolved.unknown_codes.append(code)
            continue

        bucket = CATEGORY_TO_BUCKET.get(option_info["category"], "other_options")
        getattr(resolved, bucket).append(
            ResolvedConfigurationEntry(
                code=code,
                name=option_info["name"],
            )
        )

    for accessory_key, accessory in (accessories or {}).items():
        accessory_code = _extract_accessory_code(accessory_key, accessory)
        accessory_name = BMW_ACCESSORY_MAP.get(accessory_code)
        if accessory_name is None:
            resolved.unknown_codes.append(accessory_code)
            continue
        resolved.accessories.append(
            ResolvedConfigurationEntry(
                code=accessory_code,
                name=accessory_name,
            )
        )

    return resolved


def format_resolved_configuration_items(
    resolved_configuration: ResolvedBMWConfiguration | Mapping[str, Any] | None,
) -> list[str]:
    resolved = _coerce_resolved_configuration(resolved_configuration)
    if resolved is None:
        return []

    items: list[str] = []
    if resolved.model is not None:
        items.append(f"Modell: {resolved.model.name}")
    if resolved.color is not None:
        items.append(f"Außenfarbe: {resolved.color.name}")
    if resolved.interior is not None:
        items.append(f"Innenausstattung: {resolved.interior.name}")
    items.extend(f"Paket: {entry.name}" for entry in resolved.packages)
    items.extend(entry.name for entry in resolved.wheels)
    items.extend(entry.name for entry in resolved.driver_assistance)
    items.extend(entry.name for entry in resolved.other_options)
    items.extend(f"Zubehör: {entry.name}" for entry in resolved.accessories)
    return items


def _coerce_resolved_configuration(
    resolved_configuration: ResolvedBMWConfiguration | Mapping[str, Any] | None,
) -> ResolvedBMWConfiguration | None:
    if resolved_configuration is None:
        return None
    if isinstance(resolved_configuration, ResolvedBMWConfiguration):
        return resolved_configuration
    return ResolvedBMWConfiguration.model_validate(resolved_configuration)


def _deduplicate_codes(codes: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for code in codes:
        normalized = code.strip().upper()
        if normalized and normalized not in seen:
            result.append(normalized)
            seen.add(normalized)
    return result


def _extract_accessory_code(accessory_key: str, accessory: Any) -> str:
    raw_code = getattr(accessory, "accessoryId", None)
    if raw_code is None and isinstance(accessory, Mapping):
        raw_code = accessory.get("accessoryId")
    return str(raw_code or accessory_key).strip().upper()
