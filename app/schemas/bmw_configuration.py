from __future__ import annotations

from pydantic import BaseModel, Field


class ResolvedConfigurationEntry(BaseModel):
    code: str
    name: str


class ResolvedBMWConfiguration(BaseModel):
    model: ResolvedConfigurationEntry | None = None
    color: ResolvedConfigurationEntry | None = None
    interior: ResolvedConfigurationEntry | None = None
    packages: list[ResolvedConfigurationEntry] = Field(default_factory=list)
    wheels: list[ResolvedConfigurationEntry] = Field(default_factory=list)
    driver_assistance: list[ResolvedConfigurationEntry] = Field(default_factory=list)
    other_options: list[ResolvedConfigurationEntry] = Field(default_factory=list)
    accessories: list[ResolvedConfigurationEntry] = Field(default_factory=list)
    unknown_codes: list[str] = Field(default_factory=list)
