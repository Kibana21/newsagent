from __future__ import annotations
import json
import os
import warnings
from functools import lru_cache
from google.oauth2 import service_account

warnings.filterwarnings("ignore", message=".*ChatVertexAI.*deprecated.*", category=Warning)
from langchain_google_vertexai import ChatVertexAI  # noqa: E402

from src.config import VERTEX_LOCATION, VERTEX_MODEL

SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


@lru_cache(maxsize=1)
def _credentials_and_project() -> tuple:
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path or not os.path.isfile(creds_path):
        raise EnvironmentError(
            "GOOGLE_APPLICATION_CREDENTIALS must point to the service account JSON "
            f"(got: {creds_path!r})"
        )
    with open(creds_path) as f:
        project_id = json.load(f)["project_id"]
    creds = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    return creds, project_id


def get_llm(temperature: float = 0.2) -> ChatVertexAI:
    creds, project_id = _credentials_and_project()
    return ChatVertexAI(
        model=VERTEX_MODEL,
        credentials=creds,
        project=project_id,
        location=VERTEX_LOCATION,
        temperature=temperature,
        request_timeout=120,
    )
