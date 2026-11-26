import jwt
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings

jwks_client = jwt.PyJWKClient(f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json")

class SupabaseUser:
    def __init__(self, id, email):
        self.id = id
        self.email = email
        self.is_authenticated = True

class SupabaseJWTAuthentication(BaseAuthentication):
    
    def authenticate(self, request):
        auth = request.headers.get('Authorization')
        if not auth:
            return None
        parts = auth.split()
        if len(parts) != 2 or parts[0] != "Bearer":
            raise AuthenticationFailed("Invalid Authorization header")
        token = parts[1]
        try:
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(token, signing_key.key, algorithms=["ES256"], audience="authenticated")
        except jwt.PyJWTError:
            raise AuthenticationFailed("Invalid token")
        
        supabase_user = SupabaseUser(payload["sub"], payload.get("email"))
        return (supabase_user, token)
    
    def authenticate_header(self, request):
        return "Bearer"
        
