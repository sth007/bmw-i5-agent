from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from app.services.email_preview_service import EmailPreview


LOGGER = logging.getLogger(__name__)
DEFAULT_CUSTOMER_NAME = "BMW Kaufinteressent"


class EmailTemplateService:
    def __init__(self) -> None:
        template_directory = Path(__file__).resolve().parent.parent / "templates" / "emails"
        self.environment = Environment(
            loader=FileSystemLoader(str(template_directory)),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render_campaign_request(
        self,
        *,
        dealer_id: int,
        campaign_name: str,
        config_url: str,
        dealer_name: str | None,
        dealer_email: str,
        customer_name: str,
        customer_email: str | None = None,
        customer_phone: str | None = None,
        language: str = "de",
    ) -> EmailPreview:
        subject_template_name = f"campaign_request_{language}_subject.j2"
        body_template_name = f"campaign_request_{language}_body.j2"
        context = {
            "campaign_name": campaign_name,
            "config_url": config_url,
            "dealer_name": self._clean_optional_value(dealer_name),
            "customer_name": customer_name.strip() or DEFAULT_CUSTOMER_NAME,
            "customer_email": self._clean_optional_value(customer_email),
            "customer_phone": self._clean_optional_value(customer_phone),
        }

        try:
            subject_template = self.environment.get_template(subject_template_name)
            body_template = self.environment.get_template(body_template_name)
        except TemplateNotFound as exc:
            LOGGER.exception("Email template could not be loaded: %s", exc.name)
            raise RuntimeError("Email template could not be loaded.") from exc

        subject = subject_template.render(**context).strip()
        body = body_template.render(**context).strip()

        return EmailPreview(
            dealer_id=dealer_id,
            dealer_name=self._clean_optional_value(dealer_name),
            to=dealer_email.strip(),
            subject=subject,
            body=body,
        )

    @staticmethod
    def _clean_optional_value(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None
