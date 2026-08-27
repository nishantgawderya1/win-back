"""Outreach channels — mocked but typed realistically.

WhatsApp / SMS / Email are simulated (no real provider in the buildathon
scope). Hinglish SMS templates are the India-first recovery channel.
"""
from __future__ import annotations

HINGLISH_TEMPLATES: dict[str, str] = {
    "upi_timeout": (
        "Namaste {name}, aapka Rs.{amount} ka payment thodi der pehle fail ho gaya. "
        "Network issue tha. Abhi try karein: {link}. "
        "Koi problem ho toh reply karein."
    ),
    "card_insufficient": (
        "Hi {name}, aapka Rs.{amount} ka payment decline ho gaya. "
        "Convenient time par yahan se complete karein: {link}. "
        "Help chahiye toh reply HELP."
    ),
    "checkout_abandoned": (
        "Namaste {name}! Aapne Rs.{amount} ka order incomplete chod diya. "
        "Abhi bhi available hai: {link}. "
        "Reply STOP to unsubscribe."
    ),
    "subscription_failed": (
        "Hi {name}, aapki Rs.{amount}/month subscription renew nahi hui. "
        "Service continue karne ke liye: {link}"
    ),
    "invoice_overdue": (
        "Namaste {name}, aapka Rs.{amount} ka invoice due hai. "
        "Payment karein: {link}. Dhanyavaad."
    ),
}


def render_hinglish_sms(failure_type: str, name: str | None, amount: float, link: str) -> str:
    template = HINGLISH_TEMPLATES.get(
        failure_type,
        "Hi {name}, aapka Rs.{amount} ka payment pending hai: {link}",
    )
    return template.format(name=name or "Customer", amount=int(amount), link=link)


async def send_sms(phone: str | None, message: str) -> dict:
    return {"channel": "sms", "to": phone, "delivered": bool(phone), "message": message}


async def send_whatsapp(phone: str | None, message: str) -> dict:
    return {"channel": "whatsapp", "to": phone, "delivered": bool(phone), "message": message}


async def send_email(email: str | None, subject: str, body: str) -> dict:
    return {"channel": "email", "to": email, "delivered": bool(email), "subject": subject}
