from functools import lru_cache
from typing import Annotated

import firebase_admin
from fastapi import Depends, Header, HTTPException, status
from firebase_admin import auth, credentials
from google.auth.credentials import AnonymousCredentials

from app.config import Settings, get_settings


class _NoCredentials(credentials.Base):
    """Validar tokens usa só as chaves públicas do Google; nenhuma credencial é necessária."""

    def get_credential(self) -> AnonymousCredentials:
        return AnonymousCredentials()


@lru_cache
def _firebase_app(project_id: str | None) -> firebase_admin.App:
    return firebase_admin.initialize_app(_NoCredentials(), options={"projectId": project_id})


def get_current_user(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    """Valida o token de ID do Firebase enviado como `Authorization: Bearer`."""
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token ausente.")

    try:
        return auth.verify_id_token(token, app=_firebase_app(settings.firebase_project_id))
    except auth.CertificateFetchError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Não foi possível validar o token agora."
        ) from exc
    except (ValueError, auth.InvalidIdTokenError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido.") from exc
