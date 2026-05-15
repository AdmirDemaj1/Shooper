import json
import logging
import firebase_admin
from firebase_admin import credentials, auth
from fastapi import HTTPException, status
from autoscout.settings import settings

logger = logging.getLogger(__name__)

# Initialize Firebase
try:
    if settings.FIREBASE_CREDENTIALS and settings.FIREBASE_CREDENTIALS != "{}":
        cred = credentials.Certificate(json.loads(settings.FIREBASE_CREDENTIALS))
        firebase_admin.initialize_app(cred)
    else:
        logger.warning("Firebase credentials not configured")
except Exception as e:
    logger.warning(f"Firebase initialization failed: {e}")


def verify_token(token: str) -> dict:
    # Dev mode: accept mock tokens in format "mock:<phone>"
    if settings.FASTAPI_ENV == "dev" and token.startswith("mock:"):
        phone_number = token[5:]
        if not phone_number:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid mock token")
        return {"phone_number": phone_number, "uid": f"mock-{phone_number}"}

    try:
        decoded = auth.verify_id_token(token)
        return decoded
    except auth.InvalidIdTokenError as e:
        logger.warning(f"Invalid Firebase token: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except auth.ExpiredIdTokenError as e:
        logger.warning(f"Expired Firebase token: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed")
