from __future__ import annotations

BMW_MODEL_MAP: dict[str, dict[str, str]] = {
    "51HH": {
        "model_name": "BMW i5 eDrive40 Touring",
        "variant": "eDrive40",
        "body": "Touring",
    },
}

BMW_UPHOLSTERY_MAP: dict[str, str] = {
    "FKSFU": "Veganza perforiert und gesteppt | Rauchweiß",
}

BMW_PAINT_MAP: dict[str, str] = {
    "P0A90": "Sophistograu Brillanteffekt metallic",
}

BMW_OPTION_MAP: dict[str, dict[str, str]] = {
    "S0337": {"name": "M Sportpaket", "category": "package"},
    "S03G9": {"name": "19 Zoll M Leichtmetallräder Doppelspeiche 935 M", "category": "wheels"},
    "S05AS": {"name": "Driving Assistant", "category": "driver_assistance"},
    "S05AV": {"name": "Active Guard", "category": "driver_assistance"},
}
