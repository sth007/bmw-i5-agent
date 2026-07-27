from __future__ import annotations

from app.entities.campaign_configuration import CampaignConfiguration
from app.entities.vehicle_configuration import VehicleConfiguration


def format_configuration_items(configuration: CampaignConfiguration | None) -> list[str]:
    if configuration is None:
        return []

    if configuration.vehicle_configuration is not None:
        return _format_vehicle_configuration(configuration.vehicle_configuration)

    items: list[str] = []
    for requirement in configuration.requirements:
        label = (requirement.display_label or requirement.feature_key).strip()
        if requirement.feature_value:
            items.append(f"{label}: {requirement.feature_value.strip()}")
        else:
            items.append(label)
    return items


def _format_vehicle_configuration(configuration: VehicleConfiguration) -> list[str]:
    items: list[str] = []
    if configuration.model_name:
        items.append(f"Modell: {configuration.model_name}")
    if configuration.paint_name:
        items.append(f"Außenfarbe: {configuration.paint_name}")
    if configuration.upholstery_name:
        items.append(f"Innenausstattung: {configuration.upholstery_name}")
    for feature in configuration.features:
        label = feature.display_label or feature.feature_key
        if feature.feature_value:
            items.append(f"{label}: {feature.feature_value}")
        else:
            items.append(label)
    return items
