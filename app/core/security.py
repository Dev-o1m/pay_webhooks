import hashlib
import hmac
from decimal import Decimal, ROUND_HALF_UP


MONEY_QUANT = Decimal('0.01')


def build_signature(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode('utf-8'), body, hashlib.sha256).hexdigest()


def signatures_match(secret: str, body: bytes, provided: str) -> bool:
    expected = build_signature(secret, body)
    return hmac.compare_digest(expected, provided)


def quantize_amount(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
