"""PUMP-RP-0.1 candidate reference procedure for QZC-N01-B.

This is an executable conformance reference, not production code and not a
platform-wide frozen Numeric Contract.  The ``current`` variant mirrors the
operation tree in the current pump evaluator.  ``equivalent`` is intentionally
mathematically equivalent but ordered differently so operation-order
sensitivity can be measured.
"""
from __future__ import annotations

from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
from typing import Any, Iterable

RP_ID = "PUMP-RP-0.1"
DEFAULT_PRECISION = 50
WORKING_ROUNDING = ROUND_HALF_EVEN


def decimal_input(value: Any) -> Decimal:
    """Parse canonical finite decimal input without accepting binary float."""
    if isinstance(value, (float, bool)):
        raise ValueError("canonical pump numeric input must not be binary float/bool")
    if isinstance(value, Decimal):
        result = value
    elif isinstance(value, (str, int)):
        try:
            result = Decimal(str(value).strip())
        except InvalidOperation as exc:
            raise ValueError("invalid decimal input") from exc
    else:
        raise ValueError("unsupported numeric input")
    if not result.is_finite():
        raise ValueError("numeric input must be finite")
    return result


def context_for(precision: int = DEFAULT_PRECISION) -> Context:
    if precision < 2:
        raise ValueError("precision must be >= 2")
    return Context(prec=precision, rounding=WORKING_ROUNDING)


def sqrt_ref(value: Any, precision: int = DEFAULT_PRECISION) -> Decimal:
    ctx = context_for(precision)
    with localcontext(ctx):
        x = decimal_input(value)
        if x < 0:
            raise ValueError("sqrt domain requires x >= 0")
        return x.sqrt()


def ln_ref(value: Any, precision: int = DEFAULT_PRECISION) -> Decimal:
    ctx = context_for(precision)
    with localcontext(ctx):
        x = decimal_input(value)
        if x <= 0:
            raise ValueError("ln domain requires x > 0")
        return x.ln()


def fractional_power_ref(base: Any, exponent: Any, precision: int = DEFAULT_PRECISION) -> Decimal:
    ctx = context_for(precision)
    with localcontext(ctx):
        b = decimal_input(base)
        e = decimal_input(exponent)
        if b <= 0:
            raise ValueError("fractional power reference requires base > 0")
        return ctx.power(b, e)


def specific_speed(
    *,
    QBEP: Any,
    HBEP: Any,
    speed: Any,
    suction: str,
    stages: Any,
    precision: int = DEFAULT_PRECISION,
    variant: str = "current",
) -> dict[str, Decimal]:
    """Execute the candidate specific-speed operation tree.

    ``current`` mirrors production exactly:
      q_m3h = Q / S; q_m3s = q_m3h / 3600; h_stage = H / N;
      hp = Context.power(h_stage, .75);
      ns = 3.65 * n * sqrt(q_m3s) / hp.

    ``equivalent`` combines the Q denominator, constructs h^.75 as
    sqrt(h)*sqrt(sqrt(h)), and changes multiplication/division association.
    It exists only as a sensitivity probe.
    """
    ctx = context_for(precision)
    with localcontext(ctx):
        q = decimal_input(QBEP)
        h = decimal_input(HBEP)
        n = decimal_input(speed)
        stage = decimal_input(stages)
        if q <= 0 or h <= 0 or n <= 0:
            raise ValueError("Q/H/speed must be positive")
        if stage <= 0 or stage != stage.to_integral_value():
            raise ValueError("stages must be a positive integer")
        if suction not in {"单吸", "双吸"}:
            raise ValueError("suction must be 单吸 or 双吸")
        s = Decimal("2") if suction == "双吸" else Decimal("1")

        if variant == "current":
            q_for_ns_m3h = q / s
            q_for_ns_m3s = q_for_ns_m3h / Decimal("3600")
            h_for_ns_m = h / stage
            sqrt_q = q_for_ns_m3s.sqrt()
            head_power = ctx.power(h_for_ns_m, Decimal("0.75"))
            ns = Decimal("3.65") * n * sqrt_q / head_power
        elif variant == "equivalent":
            q_for_ns_m3h = q / s
            q_for_ns_m3s = q / (s * Decimal("3600"))
            h_for_ns_m = h / stage
            sqrt_q = q_for_ns_m3s.sqrt()
            sqrt_h = h_for_ns_m.sqrt()
            fourth_root_h = sqrt_h.sqrt()
            head_power = sqrt_h * fourth_root_h
            ns = (n * Decimal("3.65") / head_power) * sqrt_q
        else:
            raise ValueError(f"unknown variant: {variant}")

        return {
            "suction_factor": s,
            "stage_count": stage,
            "q_for_ns_m3h": q_for_ns_m3h,
            "q_for_ns_m3s": q_for_ns_m3s,
            "h_for_ns_m": h_for_ns_m,
            "sqrt_q": sqrt_q,
            "head_power_0_75": head_power,
            "ns_raw": ns,
        }


def water_thresholds(
    *,
    ns_raw: Any,
    QBEP: Any,
    coefficients: dict[str, Any],
    ci: Iterable[Any],
    precision: int = DEFAULT_PRECISION,
    variant: str = "current",
) -> dict[str, Any]:
    ctx = context_for(precision)
    with localcontext(ctx):
        ns = decimal_input(ns_raw)
        q = decimal_input(QBEP)
        if ns <= 0 or q <= 0:
            raise ValueError("ln domain requires ns and Q > 0")
        c = {key: decimal_input(value) for key, value in coefficients.items()}
        ln_ns = ns.ln()
        ln_q = q.ln()
        if variant == "current":
            base = (
                c["a"] * ln_ns ** 2
                + c["b"] * ln_q ** 2
                + c["c"] * ln_ns * ln_q
                + c["d"] * ln_ns
                + c["e"] * ln_q
            )
        elif variant == "equivalent":
            terms = [
                c["e"] * ln_q,
                c["d"] * ln_ns,
                (c["c"] * ln_q) * ln_ns,
                c["b"] * (ln_q * ln_q),
                c["a"] * (ln_ns * ln_ns),
            ]
            base = sum(terms, Decimal("0"))
        else:
            raise ValueError(f"unknown variant: {variant}")
        thresholds = tuple(base - decimal_input(x) for x in ci)
        return {"ln_ns": ln_ns, "ln_q": ln_q, "base": base, "thresholds": thresholds}


def _power_sum(coefficients: Iterable[Any], x: Decimal) -> Decimal:
    coefficients = [decimal_input(c) for c in coefficients]
    return sum((coef * x ** (len(coefficients) - 1 - idx) for idx, coef in enumerate(coefficients)), Decimal("0"))


def _horner(coefficients: Iterable[Any], x: Decimal) -> Decimal:
    result = Decimal("0")
    for coefficient in coefficients:
        result = result * x + decimal_input(coefficient)
    return result


def chemical_thresholds(
    *,
    ns_raw: Any,
    QBEP: Any,
    eta_coefficients: Iterable[Any],
    delta_coefficients: Iterable[Any] | None,
    offsets: Iterable[Any],
    precision: int = DEFAULT_PRECISION,
    variant: str = "current",
) -> dict[str, Any]:
    ctx = context_for(precision)
    with localcontext(ctx):
        ns = decimal_input(ns_raw)
        q = min(decimal_input(QBEP), Decimal("3000"))
        if ns <= 0 or q <= 0:
            raise ValueError("chemical reference requires ns and Q > 0")
        ln_q = q.ln()
        if variant == "current":
            eta_b = _power_sum(eta_coefficients, ln_q)
            delta_eta = Decimal("0") if delta_coefficients is None else _power_sum(delta_coefficients, ns)
        elif variant == "equivalent":
            eta_b = _horner(eta_coefficients, ln_q)
            delta_eta = Decimal("0") if delta_coefficients is None else _horner(delta_coefficients, ns)
        else:
            raise ValueError(f"unknown variant: {variant}")
        eta_0 = eta_b - delta_eta
        thresholds = tuple(eta_0 + decimal_input(x) for x in offsets)
        return {
            "ln_q": ln_q,
            "eta_b": eta_b,
            "delta_eta": delta_eta,
            "eta_0": eta_0,
            "thresholds": thresholds,
        }


def grade_gte(actual: Any, thresholds: Iterable[Any]) -> str:
    """Business comparison is exact/full-value; no conformance tolerance here."""
    value = decimal_input(actual)
    for grade, threshold in zip(("1", "2", "3"), thresholds):
        if value >= decimal_input(threshold):
            return grade
    return "BELOW_MINIMUM"


def chemical_ns_bucket(ns_raw: Any) -> str:
    ns = decimal_input(ns_raw)
    if Decimal("20") <= ns < Decimal("60"):
        return "20<=ns<60"
    if Decimal("60") <= ns < Decimal("120"):
        return "60<=ns<120"
    if Decimal("120") <= ns <= Decimal("210"):
        return "120<=ns<=210"
    if Decimal("210") < ns <= Decimal("300"):
        return "210<ns<=300"
    return "OUT_OF_SCOPE"


def tolerance_seed(reference: Any, kind: str) -> Decimal:
    """Design-stage experimental tolerance only; never use for business logic."""
    ref = abs(decimal_input(reference))
    if kind == "T-NL-ATOM":
        return max(Decimal("1E-13"), Decimal("1E-13") * ref)
    if kind == "T-NL-COMPOSITE":
        return max(Decimal("1E-10"), Decimal("1E-12") * ref)
    raise ValueError(f"unknown tolerance seed: {kind}")


def within_seed(actual: Any, reference: Any, kind: str) -> bool:
    a = decimal_input(actual)
    r = decimal_input(reference)
    return abs(a - r) <= tolerance_seed(r, kind)
