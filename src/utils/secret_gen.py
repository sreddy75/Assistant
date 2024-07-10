import secrets
import base64

# Generate a 32-byte (256-bit) random key
random_bytes = secrets.token_bytes(32)

# Convert it to a URL-safe base64-encoded string
secret_key = base64.urlsafe_b64encode(random_bytes).decode('utf-8')

print(f"Your new secret key is: {secret_key}")
print("Make sure to keep this key secret and don't share it publicly!")