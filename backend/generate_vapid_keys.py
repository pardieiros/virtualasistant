#!/usr/bin/env python3
"""
Script to generate VAPID keys for Web Push Notifications.
Run this script to generate the public and private keys needed for push notifications.
"""

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import base64

def generate_vapid_keys():
    """Generate VAPID keys for web push notifications using cryptography library."""
    # Generate private key using SECP256R1 curve (P-256)
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    public_key = private_key.public_key()
    
    # Get public key in uncompressed format (65 bytes: 0x04 + 32 bytes X + 32 bytes Y)
    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )
    
    # Remove the 0x04 prefix (first byte) to get the raw 64-byte public key
    public_key_raw = public_key_bytes[1:]
    
    # Get private key in raw format (32 bytes)
    # Extract the private key value as bytes
    private_numbers = private_key.private_numbers()
    private_key_bytes = private_numbers.private_value.to_bytes(32, byteorder='big')
    
    # Encode to base64 URL-safe string (without padding)
    public_key_b64 = base64.urlsafe_b64encode(public_key_raw).decode('utf-8').rstrip('=')
    private_key_b64 = base64.urlsafe_b64encode(private_key_bytes).decode('utf-8').rstrip('=')
    
    print("=" * 60)
    print("VAPID Keys Generated Successfully!")
    print("=" * 60)
    print("\nAdd these to your backend/.env file:\n")
    print(f"VAPID_PUBLIC_KEY={public_key_b64}")
    print(f"VAPID_PRIVATE_KEY={private_key_b64}")
    print(f"VAPID_EMAIL=mailto:your-email@example.com")
    print("\n" + "=" * 60)
    print("Note: Replace 'your-email@example.com' with your actual email")
    print("=" * 60)

if __name__ == '__main__':
    generate_vapid_keys()

