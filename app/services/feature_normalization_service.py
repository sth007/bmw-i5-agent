from __future__ import annotations

import re
import unicodedata


class FeatureNormalizationService:
    BOOL_TRUE_VALUES = {"yes", "true", "1", "ja", "inklusive", "vorhanden"}
    BOOL_FALSE_VALUES = {"no", "false", "0", "nein", "nicht", "ohne"}

    def normalize_key(self, value: str) -> str:
        ascii_value = self._to_ascii(value)
        normalized = re.sub(r"[^a-z0-9]+", "_", ascii_value.lower()).strip("_")
        return normalized

    def normalize_value(self, value: str | None) -> str | None:
        if value is None:
            return None

        cleaned = re.sub(r"\s+", " ", self._to_ascii(value).lower()).strip()
        if cleaned in self.BOOL_TRUE_VALUES:
            return "true"
        if cleaned in self.BOOL_FALSE_VALUES:
            return "false"
        return cleaned or None

    def normalize_feature(self, feature_key: str, feature_value: str | None) -> tuple[str, str | None]:
        return self.normalize_key(feature_key), self.normalize_value(feature_value)

    @staticmethod
    def _to_ascii(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value)
        return normalized.encode("ascii", "ignore").decode("ascii")
