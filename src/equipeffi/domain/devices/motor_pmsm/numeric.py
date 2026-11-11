"""GB 30253 exact finite-decimal ingress and rational evaluation profile."""
from decimal import Decimal
from fractions import Fraction
import re

PROFILE_ID = "EQUIPEFFI_MOTOR_PMSM_EXACT_LINEAR_V1"
PROFILE_VERSION = "1.0.0"
DECIMAL_TEXT = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")


def exact_decimal(raw: object) -> Fraction:
    if isinstance(raw, bool) or not isinstance(raw, (str, int, Decimal)):
        raise ValueError("需要精确十进制词法，拒绝float")
    if isinstance(raw, int) and raw.bit_length() > 100:
        raise ValueError("整数超过输入上限")
    text = str(raw).strip()
    if len(text) > 128 or DECIMAL_TEXT.fullmatch(text) is None:
        raise ValueError("无效十进制词法")
    mantissa, _, exponent = text.lower().partition("e")
    if sum(character.isdigit() for character in mantissa) > 30 or abs(int(exponent or "0")) > 30:
        raise ValueError("数值超过输入上限")
    return Fraction(text)


def frequency_evidence(raw: object) -> bool:
    if not isinstance(raw, str) or len(raw) > 128:
        return False
    text = raw.strip()
    if not text or text.startswith(("=", "#", "@")) or DECIMAL_TEXT.fullmatch(text):
        return False
    if re.fullmatch(r"[+-]?(?:s?nan[0-9]*|inf(?:inity)?)", text, flags=re.IGNORECASE):
        return False
    if text.startswith("+") and re.search(r"[A-Za-z(]", text):
        return False
    if re.fullmatch(r"[\s+\-0-9.,eE]+", text):
        return re.fullmatch(r"[0-9]+(?:\.[0-9]+)?\s*-\s*[0-9]+(?:\.[0-9]+)?", text) is not None
    return True


def fraction_snapshot(number: Fraction) -> dict[str, str]:
    return {"numerator": str(number.numerator), "denominator": str(number.denominator)}


def efficiency_display(number: Fraction) -> str:
    whole, remainder = divmod(number.numerator * 100, number.denominator)
    whole += int(remainder * 2 >= number.denominator)
    return f"{whole // 100}.{whole % 100:02d}"
