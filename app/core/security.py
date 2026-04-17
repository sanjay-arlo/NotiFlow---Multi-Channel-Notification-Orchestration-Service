"""
Security utilities for NotiFlow.
"""

import hashlib
import hmac
import time
from typing import Optional

from passlib.context import CryptContext


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_webhook_signature(
    payload: str, secret: str, timestamp: Optional[int] = None
) -> str:
    """
    Generate webhook signature.
    
    Args:
        payload: The request payload as string
        secret: The webhook secret
        timestamp: Optional timestamp (defaults to current time)
    
    Returns:
        Signature header value in format "t=timestamp,v1=signature"
    """
    if timestamp is None:
        timestamp = int(time.time())
    
    signed_payload = f"{timestamp}.{payload}"
    signature = hmac.new(
        secret.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    
    return f"t={timestamp},v1={signature}"


def verify_webhook_signature(
    payload: str, signature_header: str, secret: str, tolerance_seconds: int = 300
) -> bool:
    """
    Verify webhook signature.
    
    Args:
        payload: The request payload as string
        signature_header: The X-Signature header value
        secret: The webhook secret
        tolerance_seconds: Time tolerance in seconds (default 5 minutes)
    
    Returns:
        True if signature is valid, False otherwise
    """
    try:
        # Parse signature header
        parts = dict(part.split("=", 1) for part in signature_header.split(","))
        timestamp = int(parts["t"])
        received_signature = parts["v1"]
        
        # Check timestamp tolerance
        current_time = int(time.time())
        if abs(current_time - timestamp) > tolerance_seconds:
            return False
        
        # Generate expected signature
        expected_signature = generate_webhook_signature(payload, secret, timestamp)
        expected_parts = dict(part.split("=", 1) for part in expected_signature.split(","))
        
        # Compare signatures
        return hmac.compare_digest(received_signature, expected_parts["v1"])
    
    except (ValueError, KeyError):
        return False


def generate_api_key() -> str:
    """Generate a new API key."""
    import secrets
    
    return f"nf_live_{secrets.token_urlsafe(32)}"


def extract_api_key_prefix(api_key: str) -> str:
    """Extract the prefix from an API key for display."""
    if len(api_key) >= 16:
        return api_key[:16]
    return api_key
