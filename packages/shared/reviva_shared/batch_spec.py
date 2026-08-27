"""Labeled failure mix for the evaluation harness. Not live traffic."""

CAUSES = (
    ("insufficient_funds", 40, "insufficient_funds", "Payment failed due to insufficient funds"),
    ("bank_downtime", 25, "gateway_error", "Issuer bank is down (U28)"),
    ("auth_failure", 20, "authentication_failed", "3DS authentication failed"),
    ("abandonment", 15, None, "checkout abandoned / user dropped"),
)


def build_specs(n: int = 100) -> list[dict]:
    specs: list[dict] = []
    i = 0
    for cause, pct, reason, desc in CAUSES:
        count = round(n * pct / 100)
        for _ in range(count):
            i += 1
            ambiguous = i % 11 == 0
            specs.append(
                {
                    "ground_truth": cause,
                    "error_reason": None if ambiguous else reason,
                    "error_description": "unclear gateway response code ZX-99" if ambiguous else desc,
                    "error_code": "UNKNOWN" if ambiguous else "BAD_REQUEST_ERROR",
                    "amount_paise": 1_200_000 if i == 3 else 49900 + (i * 100) % 200000,
                    "customer_email": f"c{i}@example.test",
                    "razorpay_payment_id": f"pay_sim_{i:04d}",
                }
            )
    return specs[:n]
