import re


# Email regex pattern - matches common email formats
EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
)

# Phone regex pattern - matches US phone formats:
# 2831823829, (283)-182-3829, (283) 182 3829, 283-182-3829
PHONE_PATTERN = re.compile(
    r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
)

# IPv4 regex pattern - matches 4 octets (0-255) separated by dots
IP_PATTERN = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
)


def mask_emails(text: str) -> tuple[str, int]:
    """Mask email addresses in text.
    
    Returns:
        A tuple of (masked_text, num_masked).
    """
    matches = EMAIL_PATTERN.findall(text)
    masked_text = EMAIL_PATTERN.sub("|||EMAIL_ADDRESS|||", text)
    return masked_text, len(matches)


def mask_phone_numbers(text: str) -> tuple[str, int]:
    """Mask phone numbers in text.
    
    Returns:
        A tuple of (masked_text, num_masked).
    """
    matches = PHONE_PATTERN.findall(text)
    masked_text = PHONE_PATTERN.sub("|||PHONE_NUMBER|||", text)
    return masked_text, len(matches)


def mask_ips(text: str) -> tuple[str, int]:
    """Mask IPv4 addresses in text.
    
    Returns:
        A tuple of (masked_text, num_masked).
    """
    matches = IP_PATTERN.findall(text)
    masked_text = IP_PATTERN.sub("|||IP_ADDRESS|||", text)
    return masked_text, len(matches)
