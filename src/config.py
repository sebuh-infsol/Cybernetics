import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Google Cloud / Gemini
    GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

    # Dynatrace
    DYNATRACE_ENVIRONMENT_ID = os.getenv("DYNATRACE_ENVIRONMENT_ID", "")
    DYNATRACE_API_TOKEN = os.getenv("DYNATRACE_API_TOKEN", "")
    DYNATRACE_BASE_URL = os.getenv("DYNATRACE_BASE_URL", "")

    # Elastic
    ELASTIC_CLOUD_ID = os.getenv("ELASTIC_CLOUD_ID", "")
    ELASTIC_API_KEY = os.getenv("ELASTIC_API_KEY", "")

    # MongoDB
    MONGODB_URI = os.getenv("MONGODB_URI", "")

    # GitLab
    GITLAB_URL = os.getenv("GITLAB_URL", "https://gitlab.com")
    GITLAB_TOKEN = os.getenv("GITLAB_TOKEN", "")
    GITLAB_PROJECT_ID = os.getenv("GITLAB_PROJECT_ID", "")

    # Arize
    ARIZE_API_KEY = os.getenv("ARIZE_API_KEY", "")
    ARIZE_ENDPOINT = os.getenv("ARIZE_ENDPOINT", "https://app.phoenix.arize.com")

    # Fivetran
    FIVETRAN_API_KEY = os.getenv("FIVETRAN_API_KEY", "")
    FIVETRAN_API_SECRET = os.getenv("FIVETRAN_API_SECRET", "")

    @classmethod
    def validate(cls):
        required = [
            "GOOGLE_CLOUD_PROJECT",
            "GEMINI_API_KEY",
            "MONGODB_URI",
            "GITLAB_TOKEN",
            "ARIZE_API_KEY",
        ]
        missing = [r for r in required if not getattr(cls, r)]
        if missing:
            raise ValueError(f"Missing required env vars: {', '.join(missing)}")
