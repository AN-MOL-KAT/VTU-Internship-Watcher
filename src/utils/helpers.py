import re
from typing import Optional, Tuple


def clean_text(text: Optional[str]) -> str:
    """Removes extra whitespace, non-breaking spaces, and leading/trailing blanks."""
    if not text:
        return ""
    # Replace non-breaking spaces and clean whitespace
    cleaned = text.replace("\xa0", " ").replace("&nbsp;", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def parse_fee_amount(fee_str: Optional[str]) -> float:
    """
    Extracts numerical fee amount from strings like:
    '₹3,999', 'Rs 1500', '1,500.00', 'Free', 'Nil', '0'
    Returns 0.0 for free/stipend or missing values, or positive float.
    """
    if not fee_str:
        return 0.0

    lower = fee_str.lower()
    if any(keyword in lower for keyword in ["free", "nil", "na", "n/a", "none", "0"]):
        # Check if there is still a non-zero number (e.g. 'not free: 1500')
        if not re.search(r"\d+", fee_str):
            return 0.0

    # Extract digits with optional commas and decimals
    matches = re.findall(r"[\d,]+(?:\.\d+)?", fee_str)
    if not matches:
        return 0.0

    # Clean the first numeric match
    num_str = matches[0].replace(",", "")
    try:
        return float(num_str)
    except ValueError:
        return 0.0


def normalize_mode(mode_str: Optional[str]) -> str:
    """
    Normalizes internship mode to 'Remote', 'Hybrid', or 'Onsite'.
    """
    if not mode_str:
        return "Unknown"

    text = mode_str.lower()
    if any(k in text for k in ["remote", "online", "virtual", "wfh", "work from home"]):
        return "Remote"
    elif any(k in text for k in ["hybrid", "blended"]):
        return "Hybrid"
    elif any(k in text for k in ["onsite", "offline", "in-person", "in person", "office"]):
        return "Onsite"
    return "Onsite"  # Default if unspecified


def normalize_type(
    type_str: Optional[str], fee: float = 0.0, stipend: Optional[str] = None
) -> str:
    """
    Normalizes internship type to 'Stipend', 'Free', or 'Paid'.
    """
    if stipend and clean_text(stipend):
        stip_lower = stipend.strip().lower()
        if stip_lower not in ["0", "nil", "none", "na", "n/a", "no stipend", "unpaid", "-"]:
            if not any(neg in stip_lower for neg in ["no stipend", "unpaid", "not applicable"]):
                return "Stipend"

    combined = f"{type_str or ''} {stipend or ''}".lower()

    if any(k in combined for k in ["stipend", "paid by company", "stipendiary"]):
        return "Stipend"

    if fee > 0:
        return "Paid"

    if any(k in combined for k in ["paid", "registration fee", "course fee"]):
        return "Paid"

    return "Free"


def format_currency(amount: float) -> str:
    """Formats numeric amount into readable INR string."""
    if amount == 0:
        return "₹0 (Free)"
    return f"₹{amount:,.2f}".rstrip("0").rstrip(".")
