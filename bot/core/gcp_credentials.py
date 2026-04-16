"""Загрузка учётных данных GCP для Vertex / REST с явным scope cloud-platform.

Без scope вызов google.auth.default() + refresh() может давать invalid_scope на VM вне GCP.
"""
from __future__ import annotations

import os
from typing import Optional

from google.auth.credentials import Credentials
from google.auth import default as adc_default
from google.oauth2 import service_account

_CLOUD_PLATFORM = ("https://www.googleapis.com/auth/cloud-platform",)


def load_cloud_platform_credentials() -> Credentials:
    """Service account из GOOGLE_APPLICATION_CREDENTIALS или ADC с нужным scope."""
    path: Optional[str] = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if path and os.path.isfile(path):
        return service_account.Credentials.from_service_account_file(
            path,
            scopes=_CLOUD_PLATFORM,
        )
    credentials, _ = adc_default(scopes=list(_CLOUD_PLATFORM))
    return credentials
