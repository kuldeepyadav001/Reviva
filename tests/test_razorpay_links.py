import os

from reviva_shared.razorpay_links import create_payment_link, keys_configured


def test_placeholder_keys_are_not_configured(monkeypatch):
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_xxxxxxxx")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "replace_me")
    assert keys_configured() is False


def test_stub_when_unconfigured(monkeypatch):
    monkeypatch.delenv("RAZORPAY_KEY_ID", raising=False)
    monkeypatch.delenv("RAZORPAY_KEY_SECRET", raising=False)
    out = create_payment_link(100, "pay_1", "a@b.test", "x")
    assert out["stub"] is True
    assert out["id"].startswith("plink_stub_")
