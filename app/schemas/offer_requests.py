from pydantic import BaseModel


class ExtractOfferRequest(BaseModel):
    text: str

    campaign_id: str
    configuration_id: str
    dealer_id: str

    email_subject: str | None = None
    email_text: str | None = None
    pdf_filename: str | None = None