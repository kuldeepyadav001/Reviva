from reviva_shared.hmac_util import razorpay_webhook_signature, verify_razorpay_signature


def test_signature_roundtrip():
    body = b'{"event":"payment.failed"}'
    secret = "whsec_test"
    sig = razorpay_webhook_signature(body, secret)
    assert verify_razorpay_signature(body, sig, secret)


def test_wrong_secret_fails():
    body = b"{}"
    sig = razorpay_webhook_signature(body, "a")
    assert not verify_razorpay_signature(body, sig, "b")


def test_missing_signature_fails():
    assert not verify_razorpay_signature(b"{}", None, "secret")
