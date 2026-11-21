import time
from uuid import UUID, uuid4

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.adapters.auth.jwt_oidc import JwtIdentityAdapter
from app.core.config import Settings
from app.ports.services import Principal


@pytest.fixture(scope="module")
def rsa_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    return private_pem, public_pem


@pytest.fixture(scope="module")
def other_rsa_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    return private_pem


def _mint_jwt(
    private_key: str,
    claims: dict,
    algorithm: str = "RS256",
    headers: dict | None = None,
) -> str:
    return jwt.encode(claims, private_key, algorithm=algorithm, headers=headers)


def test_jwt_valid_token_resolves_principal(rsa_keypair):
    private_pem, public_pem = rsa_keypair
    user_id = uuid4()
    settings = Settings(
        _env_file=None,
        app_env="production",
        jwt_public_key=public_pem,
        jwt_issuer="https://auth.example.com",
        jwt_audience="https://api.finxl.test",
        jwt_algorithms=["RS256"],
        llm_provider="gemini",
        gemini_api_key="placeholder",
        cors_allowed_origins=["https://finxl.test"],
        trusted_hosts=["finxl.test"],
        transcript_retention_days=30,
    )
    adapter = JwtIdentityAdapter(settings)
    token = _mint_jwt(
        private_pem,
        {
            "sub": str(user_id),
            "iss": "https://auth.example.com",
            "aud": "https://api.finxl.test",
            "exp": time.time() + 300,
            "role": "student",
        },
    )

    principal = adapter.resolve(f"Bearer {token}")
    assert isinstance(principal, Principal)
    assert principal.user_id == user_id
    assert principal.role == "student"


def test_jwt_rejects_expired_token(rsa_keypair):
    private_pem, public_pem = rsa_keypair
    settings = Settings(
        _env_file=None,
        app_env="production",
        jwt_public_key=public_pem,
        jwt_issuer="https://auth.example.com",
        jwt_audience="https://api.finxl.test",
        jwt_leeway_seconds=0,
        llm_provider="gemini",
        gemini_api_key="placeholder",
        cors_allowed_origins=["https://finxl.test"],
        trusted_hosts=["finxl.test"],
        transcript_retention_days=30,
    )
    adapter = JwtIdentityAdapter(settings)
    token = _mint_jwt(
        private_pem,
        {
            "sub": str(uuid4()),
            "iss": "https://auth.example.com",
            "aud": "https://api.finxl.test",
            "exp": time.time() - 10,
        },
    )

    with pytest.raises(ValueError, match="Token has expired"):
        adapter.resolve(token)


def test_jwt_rejects_immature_token(rsa_keypair):
    private_pem, public_pem = rsa_keypair
    settings = Settings(
        _env_file=None,
        app_env="production",
        jwt_public_key=public_pem,
        jwt_leeway_seconds=0,
        llm_provider="gemini",
        gemini_api_key="placeholder",
        cors_allowed_origins=["https://finxl.test"],
        trusted_hosts=["finxl.test"],
        transcript_retention_days=30,
    )
    adapter = JwtIdentityAdapter(settings)
    token = _mint_jwt(
        private_pem,
        {
            "sub": str(uuid4()),
            "exp": time.time() + 300,
            "nbf": time.time() + 100,
        },
    )

    with pytest.raises(ValueError, match="Token not valid yet"):
        adapter.resolve(token)


def test_jwt_rejects_issuer_mismatch(rsa_keypair):
    private_pem, public_pem = rsa_keypair
    settings = Settings(
        _env_file=None,
        app_env="production",
        jwt_public_key=public_pem,
        jwt_issuer="https://trusted.issuer.com",
        llm_provider="gemini",
        gemini_api_key="placeholder",
        cors_allowed_origins=["https://finxl.test"],
        trusted_hosts=["finxl.test"],
        transcript_retention_days=30,
    )
    adapter = JwtIdentityAdapter(settings)
    token = _mint_jwt(
        private_pem,
        {
            "sub": str(uuid4()),
            "iss": "https://untrusted.issuer.com",
            "exp": time.time() + 300,
        },
    )

    with pytest.raises(ValueError, match="Token issuer does not match trusted issuer"):
        adapter.resolve(token)


def test_jwt_rejects_audience_mismatch(rsa_keypair):
    private_pem, public_pem = rsa_keypair
    settings = Settings(
        _env_file=None,
        app_env="production",
        jwt_public_key=public_pem,
        jwt_audience="https://expected.aud",
        llm_provider="gemini",
        gemini_api_key="placeholder",
        cors_allowed_origins=["https://finxl.test"],
        trusted_hosts=["finxl.test"],
        transcript_retention_days=30,
    )
    adapter = JwtIdentityAdapter(settings)
    token = _mint_jwt(
        private_pem,
        {
            "sub": str(uuid4()),
            "aud": "https://wrong.aud",
            "exp": time.time() + 300,
        },
    )

    with pytest.raises(ValueError, match="Token audience does not match trusted audience"):
        adapter.resolve(token)


def test_jwt_rejects_unsigned_and_none_algorithm():
    settings = Settings(
        _env_file=None,
        app_env="test",
        jwt_public_key="some-public-key",
        jwt_algorithms=["RS256"],
    )
    adapter = JwtIdentityAdapter(settings)
    token_none = jwt.encode(
        {"sub": str(uuid4()), "exp": time.time() + 300}, key="", algorithm="none"
    )

    with pytest.raises(ValueError, match="Algorithm 'none' is not allowed"):
        adapter.resolve(token_none)


def test_jwt_rejects_unallowed_algorithm(rsa_keypair):
    settings = Settings(
        _env_file=None,
        app_env="test",
        jwt_public_key="some-key",
        jwt_algorithms=["RS256"],
    )
    adapter = JwtIdentityAdapter(settings)
    token_hs = jwt.encode(
        {"sub": str(uuid4()), "exp": time.time() + 300},
        key="x" * 32,
        algorithm="HS256",
    )

    with pytest.raises(ValueError, match="Algorithm 'HS256' is not allowed"):
        adapter.resolve(token_hs)


def test_jwt_rejects_invalid_signature(rsa_keypair, other_rsa_keypair):
    _, public_pem = rsa_keypair
    other_private_pem = other_rsa_keypair
    settings = Settings(
        _env_file=None,
        app_env="test",
        jwt_public_key=public_pem,
        jwt_algorithms=["RS256"],
    )
    adapter = JwtIdentityAdapter(settings)
    token = _mint_jwt(other_private_pem, {"sub": str(uuid4()), "exp": time.time() + 300})

    with pytest.raises(ValueError, match="Token signature verification failed"):
        adapter.resolve(token)


def test_jwt_rejects_malformed_tokens(rsa_keypair):
    _, public_pem = rsa_keypair
    settings = Settings(_env_file=None, app_env="test", jwt_public_key=public_pem)
    adapter = JwtIdentityAdapter(settings)

    with pytest.raises(ValueError, match="Token is missing"):
        adapter.resolve("")
    with pytest.raises(ValueError, match="Malformed token"):
        adapter.resolve("not.a.valid.jwt.string")
    with pytest.raises(ValueError, match="Malformed token"):
        adapter.resolve("only-one-part")


def test_jwt_rejects_non_uuid_subject_without_mapper(rsa_keypair):
    private_pem, public_pem = rsa_keypair
    settings = Settings(_env_file=None, app_env="test", jwt_public_key=public_pem)
    adapter = JwtIdentityAdapter(settings)
    token = _mint_jwt(private_pem, {"sub": "auth0|student_abc_123", "exp": time.time() + 300})

    with pytest.raises(ValueError, match="contains a non-UUID identifier"):
        adapter.resolve(token)


def test_jwt_resolves_non_uuid_subject_with_verified_mapper(rsa_keypair):
    private_pem, public_pem = rsa_keypair
    student_uuid = uuid4()
    settings = Settings(_env_file=None, app_env="test", jwt_public_key=public_pem)

    def fake_mapper(sub: str, _claims: dict) -> UUID | None:
        if sub == "auth0|student_abc_123":
            return student_uuid
        return None

    adapter = JwtIdentityAdapter(settings, identity_mapper=fake_mapper)
    token = _mint_jwt(private_pem, {"sub": "auth0|student_abc_123", "exp": time.time() + 300})

    principal = adapter.resolve(token)
    assert principal.user_id == student_uuid


def test_jwt_rejects_unmapped_external_subject(rsa_keypair):
    private_pem, public_pem = rsa_keypair
    settings = Settings(_env_file=None, app_env="test", jwt_public_key=public_pem)

    def fake_mapper(_sub: str, _claims: dict) -> UUID | None:
        return None  # Unmapped

    adapter = JwtIdentityAdapter(settings, identity_mapper=fake_mapper)
    token = _mint_jwt(private_pem, {"sub": "unregistered_external_user", "exp": time.time() + 300})

    with pytest.raises(ValueError, match="Unknown external student identity"):
        adapter.resolve(token)


def test_jwt_resolves_configured_student_id_claim(rsa_keypair):
    private_pem, public_pem = rsa_keypair
    student_uuid = uuid4()
    settings = Settings(
        _env_file=None,
        app_env="test",
        jwt_public_key=public_pem,
        jwt_user_id_claim="student_id",
    )
    adapter = JwtIdentityAdapter(settings)
    token = _mint_jwt(
        private_pem,
        {
            "sub": "auth0|external_account_999",
            "student_id": str(student_uuid),
            "exp": time.time() + 300,
        },
    )

    principal = adapter.resolve(token)
    assert principal.user_id == student_uuid


def test_jwt_rejects_missing_configured_student_claim(rsa_keypair):
    private_pem, public_pem = rsa_keypair
    settings = Settings(
        _env_file=None,
        app_env="test",
        jwt_public_key=public_pem,
        jwt_user_id_claim="custom_student_id",
    )
    adapter = JwtIdentityAdapter(settings)
    token = _mint_jwt(
        private_pem,
        {"sub": str(uuid4()), "exp": time.time() + 300},
    )

    with pytest.raises(ValueError, match="Missing user id claim 'custom_student_id'"):
        adapter.resolve(token)


def test_jwt_rejects_malformed_configured_student_claim(rsa_keypair):
    private_pem, public_pem = rsa_keypair
    settings = Settings(
        _env_file=None,
        app_env="test",
        jwt_public_key=public_pem,
        jwt_user_id_claim="student_id",
    )
    adapter = JwtIdentityAdapter(settings)
    token = _mint_jwt(
        private_pem,
        {"sub": str(uuid4()), "student_id": "not-a-valid-uuid", "exp": time.time() + 300},
    )

    with pytest.raises(ValueError, match="contains a non-UUID identifier"):
        adapter.resolve(token)


def test_jwt_rejects_empty_user_id_claim(rsa_keypair):
    private_pem, public_pem = rsa_keypair
    settings = Settings(_env_file=None, app_env="test", jwt_public_key=public_pem)
    adapter = JwtIdentityAdapter(settings)
    token = _mint_jwt(private_pem, {"sub": "   ", "exp": time.time() + 300})

    with pytest.raises(ValueError, match="User id claim 'sub' is empty"):
        adapter.resolve(token)


def test_jwt_safe_jwks_rotation(rsa_keypair):
    private_pem, public_pem = rsa_keypair
    user_id = uuid4()
    settings = Settings(
        _env_file=None,
        app_env="test",
        jwt_jwks_url="https://auth.example.com/.well-known/jwks.json",
        jwt_algorithms=["RS256"],
    )

    class FakeSigningKey:
        def __init__(self, key: str):
            self.key = key

    class FakeJWKSClient:
        def __init__(self, key: str):
            self._key = key
            self.calls = 0

        def get_signing_key_from_jwt(self, _token: str):
            self.calls += 1
            return FakeSigningKey(self._key)

    fake_client = FakeJWKSClient(public_pem)
    adapter = JwtIdentityAdapter(settings, jwks_client=fake_client)

    token = _mint_jwt(
        private_pem,
        {"sub": str(user_id), "exp": time.time() + 300},
        headers={"kid": "key-2026-rot-1"},
    )
    principal = adapter.resolve(token)
    assert principal.user_id == user_id
    assert fake_client.calls == 1
