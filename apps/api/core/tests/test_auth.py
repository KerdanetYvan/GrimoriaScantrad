from rest_framework.test import APIClient
from cryptography.hazmat.primitives.asymmetric import ec
from datetime import datetime, timedelta, timezone
from core.authentication import jwks_client
import jwt

class FakeKey:
    def __init__(self, key):
        self.key = key


def test_me_without_token_returns_401():
    client = APIClient()
    response = client.get('/api/me/')
    
    assert response.status_code == 401
    
def test_me_with_false_token_returns_401():
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Bearer 6s5d4fds321f56sd4f654d6f4")
    response = client.get('/api/me/')
    
    assert response.status_code == 401


def test_me_with_right_token_returns_200(monkeypatch):
    private_generate_keys = ec.generate_private_key(ec.SECP256R1())
    public_generated_key = private_generate_keys.public_key()
    content = {"sub": "test_sub", "email": "test@test.com", "aud": "authenticated", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    token = jwt.encode(content, private_generate_keys, algorithm="ES256")
    def get_fake_signing_key_from_jwt(token):
        return FakeKey(public_generated_key)
    monkeypatch.setattr(jwks_client, "get_signing_key_from_jwt", get_fake_signing_key_from_jwt)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = client.get('/api/me/')
    
    assert response.status_code == 200
    assert response.json() == {"id": content.get('sub'), "email": content.get('email')}