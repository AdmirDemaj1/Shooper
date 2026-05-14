import json
import firebase_admin
from firebase_admin import credentials, auth
from autoscout.settings import settings

# Initialize Firebase
try:
    if settings.FIREBASE_CREDENTIALS and settings.FIREBASE_CREDENTIALS != "{}":
        cred = credentials.Certificate(json.loads(settings.FIREBASE_CREDENTIALS))
        firebase_admin.initialize_app(cred)
except Exception as e:
    print(f"Warning: Firebase not initialized: {e}")


def verify_token(token: str) -> dict | None:
    try:
        decoded = auth.verify_id_token(token)
        return decoded
    except Exception as e:
        print(f"Token verification failed: {e}")
        return None
