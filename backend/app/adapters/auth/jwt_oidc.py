import logging
from collections.abc import Callable
from typing import Any
from uuid import UUID

import jwt
from jwt import PyJWKClient

from app.core.config import Settings
from app.ports.authentication import IdentityProvider
from app.ports.services import Principal

logger = logging.getLogger(__name__)

IdentityMapper = Callable[[str, dict[str, Any]], UUID | None]


class JwtIdentityAdapter(IdentityProvider):
    """Standards-based JWT/OIDC identity verifier using configurable settings."""

    def __init__(
        self,
        settings: Settings,
        jwks_client: Any | None = None,
        identity_mapper: IdentityMapper | None = None,
    ) -> None:
        self._settings = settings
        self._jwks_client: Any | None = jwks_client
        self._identity_mapper: IdentityMapper | None = identity_mapper
        if self._jwks_client is None and settings.jwt_jwks_url:
            self._jwks_client = PyJWKClient(
                uri=settings.jwt_jwks_url,
                cache_keys=True,
                max_cached_keys=16,
                cache_jwk_set=True,
                lifespan=300,
            )

    def resolve(self, presented_identity: str | None) -> Principal:
        if not presented_identity:
            raise ValueError("Token is missing")

        raw_token = presented_identity.strip()
        if raw_token.lower().startswith("bearer "):
            raw_token = raw_token[7:].strip()

        if not raw_token:
            raise ValueError("Token is missing")

        token_parts = raw_token.split(".")
        if len(token_parts) != 3:
            raise ValueError("Malformed token")

        allowed_algorithms = [alg.upper() for alg in self._settings.jwt_algorithms]

        try:
            unverified_header = jwt.get_unverified_header(raw_token)
        except Exception as exc:
            raise ValueError("Malformed token header") from exc

        alg = unverified_header.get("alg")
        if not alg or alg.upper() == "NONE" or alg.upper() not in allowed_algorithms:
            raise ValueError(f"Algorithm '{alg}' is not allowed")

        key: Any
        if self._jwks_client is not None:
            try:
                signing_key = self._jwks_client.get_signing_key_from_jwt(raw_token)
                key = signing_key.key
            except Exception as exc:
                logger.warning("JWKS key resolution failed (%s)", type(exc).__name__)
                raise ValueError("Signing key could not be retrieved from JWKS") from exc
        elif self._settings.jwt_public_key:
            key = self._settings.jwt_public_key.strip()
        else:
            raise ValueError("No verification key configured for production JWT adapter")

        try:
            payload = jwt.decode(
                raw_token,
                key,
                algorithms=allowed_algorithms,
                issuer=self._settings.jwt_issuer,
                audience=self._settings.jwt_audience,
                leeway=self._settings.jwt_leeway_seconds,
                options={"require": ["exp", "sub"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise ValueError("Token has expired") from exc
        except jwt.ImmatureSignatureError as exc:
            raise ValueError("Token not valid yet (nbf claim)") from exc
        except jwt.InvalidIssuerError as exc:
            raise ValueError("Token issuer does not match trusted issuer") from exc
        except jwt.InvalidAudienceError as exc:
            raise ValueError("Token audience does not match trusted audience") from exc
        except jwt.InvalidAlgorithmError as exc:
            raise ValueError("Token algorithm is not allowed") from exc
        except jwt.InvalidSignatureError as exc:
            raise ValueError("Token signature verification failed") from exc
        except (jwt.DecodeError, jwt.InvalidTokenError) as exc:
            raise ValueError("Token is invalid") from exc

        user_id_claim = self._settings.jwt_user_id_claim
        raw_user_id = payload.get(user_id_claim)
        if not raw_user_id:
            raise ValueError(f"Missing user id claim '{user_id_claim}'")

        raw_str = str(raw_user_id).strip()
        if not raw_str:
            raise ValueError(f"User id claim '{user_id_claim}' is empty")

        user_id: UUID | None = None
        try:
            user_id = UUID(raw_str)
        except (ValueError, TypeError, AttributeError):
            user_id = None

        if user_id is None:
            if self._identity_mapper is not None:
                try:
                    mapped = self._identity_mapper(raw_str, payload)
                except Exception as exc:
                    logger.warning("Identity mapper lookup failed (%s)", type(exc).__name__)
                    raise ValueError(f"External identity mapping failed for '{raw_str}'") from exc
                if mapped is None or not isinstance(mapped, UUID):
                    raise ValueError(f"Unknown external student identity '{raw_str}'")
                user_id = mapped
            else:
                raise ValueError(
                    f"Claim '{user_id_claim}' contains a non-UUID identifier '{raw_str}'. "
                    "External non-UUID identities require an explicit student UUID claim "
                    "or a configured identity mapping; implicit identity synthesis is disabled."
                )

        role = "student"
        role_claim = self._settings.jwt_role_claim
        if role_claim and role_claim in payload:
            raw_role = payload[role_claim]
            if isinstance(raw_role, list) and raw_role:
                role = str(raw_role[0])
            elif isinstance(raw_role, str) and raw_role:
                role = raw_role

        return Principal(user_id=user_id, role=role)
