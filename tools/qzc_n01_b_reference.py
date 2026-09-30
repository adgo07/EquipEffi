from __future__ import annotations

from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
from typing import Any, Iterable

PROFILE_ID = "PUMP-RP-0.1"
DEFAULT_PRECISION = 50
DEFAULT_ROUNDING = ROUND_HALF_EVEN


def exact_decimal(value: Any) -> Decimal:
    if isinstance(value, float) or isinstance(value, bool):
        raise ValueError("reference procedure rejects binary float/bool")
    if isinstance(value, Decimal):
        out = value
    elif isinstance(value, (str, int)):
        try:
            out = Decimal(str(value).strip())
        except InvalidOperation as exc:
            raise ValueError("invalid decimal input") from exc
    else:
        raise ValueError("reference procedure requires decimal text, Decimal, or int")
    if not out.is_finite():
        raise ValueError("reference procedure requires finite decimal input")
    return out


def make_context(precision: int = DEFAULT_PRECISION) -> Context:
    return Context(prec=precision, rounding=DEFAULT_ROUNDING)


def specific_speed(inputs: dict[str, Any], precision: int = DEFAULT_PRECISION) -> dict[str, Decimal]:
    ctx = make_context(precision)
    with localcontext(ctx):
        q = exact_decimal(inputs["QBEP"])
        h = exact_decimal(inputs["HBEP"])
        speed = exact_decimal(inputs["speed"])
        stages = exact_decimal(inputs["stages"])
        suction = str(inputs["suction"]).strip()
        if q <= 0 or h <= 0 or speed <= 0:
            raise ValueError("Q/H/speed must be positive")
        if stages <= 0 or stages != stages.to_integral_value():
            raise ValueError("stages must be a positive integer")
        if suction not in {"单吸", "双吸"}:
            raise ValueError("suction must be 单吸 or 双吸")
        s = Decimal("2") if suction == "双吸" else Decimal("1")
        q_ns_m3h = q / s
        q_ns = q_ns_m3h / Decimal("3600")
        h_ns = h / stages
        sqrt_q = q_ns.sqrt()
        h_pow = ctx.power(h_ns, Decimal("0.75"))
        ns = Decimal("3.65") * speed * sqrt_q / h_pow
        return {
            "q_ns_m3h": q_ns_m3h,
            "q_ns_m3s": q_ns,
            "h_ns": h_ns,
            "sqrt_q_ns": sqrt_q,
            "h_pow_0_75": h_pow,
            "ns_raw": ns,
        }


def specific_speed_alt(inputs: dict[str, Any], precision: int = DEFAULT_PRECISION) -> dict[str, Decimal]:
    """Mathematically equivalent alternative tree for sensitivity experiments only."""
    ctx = make_context(precision)
    with localcontext(ctx):
        q = exact_decimal(inputs["QBEP"])
        h = exact_decimal(inputs["HBEP"])
        speed = exact_decimal(inputs["speed"])
        stages = exact_decimal(inputs["stages"])
        suction = str(inputs["suction"]).strip()
        s = Decimal("2") if suction == "双吸" else Decimal("1")
        q_ns = q / (s * Decimal("3600"))
        h_ns = h / stages
        sqrt_q = q_ns.sqrt()
        # H^(3/4) == sqrt(H) * sqrt(sqrt(H)); deliberately different tree.
        sqrt_h = h_ns.sqrt()
        h_pow = sqrt_h * sqrt_h.sqrt()
        ratio = sqrt_q / h_pow
        ns = Decimal("3.65") * (speed * ratio)
        return {
            "q_ns_m3s": q_ns,
            "h_ns": h_ns,
            "sqrt_q_ns": sqrt_q,
            "h_pow_0_75": h_pow,
            "ns_raw": ns,
        }


def clean_thresholds(ns: Any, q: Any, coeff: dict[str, Any], ci: Iterable[Any], precision: int = DEFAULT_PRECISION) -> list[Decimal]:
    ctx = make_context(precision)
    with localcontext(ctx):
        ns_d = exact_decimal(ns)
        q_d = exact_decimal(q)
        c = {k: exact_decimal(v) for k, v in coeff.items()}
        ln_ns = ns_d.ln()
        ln_q = q_d.ln()
        base = (
            c["a"] * ln_ns**2
            + c["b"] * ln_q**2
            + c["c"] * ln_ns * ln_q
            + c["d"] * ln_ns
            + c["e"] * ln_q
        )
        return [base - exact_decimal(item) for item in ci]


def clean_thresholds_alt(ns: Any, q: Any, coeff: dict[str, Any], ci: Iterable[Any], precision: int = DEFAULT_PRECISION) -> list[Decimal]:
    """Equivalent regrouping used only to expose operation-order sensitivity."""
    ctx = make_context(precision)
    with localcontext(ctx):
        ns_d = exact_decimal(ns)
        q_d = exact_decimal(q)
        c = {k: exact_decimal(v) for k, v in coeff.items()}
        ln_ns = ns_d.ln()
        ln_q = q_d.ln()
        ns_part = (c["a"] * ln_ns + c["c"] * ln_q + c["d"]) * ln_ns
        q_part = (c["b"] * ln_q + c["e"]) * ln_q
        base = ns_part + q_part
        return [base - exact_decimal(item) for item in ci]


def polynomial_current(x: Any, coefficients: Iterable[Any], precision: int = DEFAULT_PRECISION) -> Decimal:
    ctx = make_context(precision)
    coeff = [exact_decimal(v) for v in coefficients]
    with localcontext(ctx):
        x_d = exact_decimal(x)
        return sum(c * x_d ** (len(coeff) - 1 - i) for i, c in enumerate(coeff))


def polynomial_horner(x: Any, coefficients: Iterable[Any], precision: int = DEFAULT_PRECISION) -> Decimal:
    ctx = make_context(precision)
    coeff = [exact_decimal(v) for v in coefficients]
    with localcontext(ctx):
        x_d = exact_decimal(x)
        acc = Decimal("0")
        for c in coeff:
            acc = acc * x_d + c
        return acc


def tolerance_limit(reference: Decimal, kind: str) -> Decimal:
    magnitude = abs(reference)
    if kind == "T-NL-ATOM":
        return max(Decimal("1E-13"), Decimal("1E-13") * magnitude)
    if kind == "T-NL-COMPOSITE":
        return max(Decimal("1E-10"), Decimal("1E-12") * magnitude)
    raise ValueError(kind)
