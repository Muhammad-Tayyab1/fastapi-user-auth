from app.core.security import create_token, decode_token, hash_password, verify_password
from app.services.otp_service import generate_otp


def test_password_round_trip() -> None:
    hashed = hash_password("correct-horse-battery-staple")
    assert verify_password("correct-horse-battery-staple", hashed)
    assert not verify_password("wrong-password", hashed)


def test_access_token_round_trip() -> None:
    token = create_token("user-id", "access")
    assert decode_token(token, "access")["sub"] == "user-id"


def test_otp_shape() -> None:
    code = generate_otp()
    assert len(code) == 6 and code.isdigit()

