# Passkey Authentication API Documentation

This document describes how to implement passkey (WebAuthn) authentication in your frontend application.

## Overview

Passkey authentication provides a passwordless login experience using biometric authentication (Face ID, Touch ID, Windows Hello) or security keys.

## API Endpoints

### 1. Generate Authentication Challenge
**POST** `/auth/passkey/challenge/`

Generates a WebAuthn authentication challenge for passkey login.

**Request Body:**
```json
{
  "username": "user123"
}
```

**Success Response (200 OK):**
```json
{
  "options": {
    "challenge": "base64-encoded-challenge",
    "timeout": 60000,
    "rpId": "yourdomain.com",
    "allowCredentials": [
      {
        "id": "credential-id",
        "type": "public-key",
        "transports": ["internal", "usb", "nfc", "ble"]
      }
    ],
    "userVerification": "preferred"
  }
}
```

**Error Responses:**
- `400 Bad Request`: Username is required
- `404 Not Found`: User not found or no passkeys registered

---

### 2. Verify Authentication Response
**POST** `/auth/passkey/verify/`

Verifies the WebAuthn authentication response and issues JWT tokens.

**Request Body:**
```json
{
  "username": "user123",
  "credential": {
    "id": "base64-credential-id",
    "rawId": "base64-raw-id",
    "response": {
      "clientDataJSON": "base64-client-data",
      "authenticatorData": "base64-authenticator-data",
      "signature": "base64-signature",
      "userHandle": "base64-user-handle"
    },
    "type": "public-key"
  }
}
```

**Success Response (200 OK):**
```json
{
  "message": "Login successful",
  "access": "jwt-access-token",
  "refresh": "jwt-refresh-token",
  "is_admin": false,
  "username": "user123"
}
```

**Error Responses:**
- `400 Bad Request`: Missing required fields or challenge expired
- `401 Unauthorized`: Authentication failed
- `404 Not Found`: User or credential not found

---

## Frontend Implementation Example

### Using JavaScript WebAuthn API

```javascript
// 1. Request authentication challenge
async function loginWithPasskey(username) {
  try {
    // Step 1: Get challenge from server
    const challengeResponse = await fetch('/auth/passkey/challenge/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username })
    });
    
    if (!challengeResponse.ok) {
      const error = await challengeResponse.json();
      throw new Error(error.message);
    }
    
    const { options } = await challengeResponse.json();
    
    // Step 2: Convert challenge from base64
    const publicKeyCredentialRequestOptions = {
      ...options,
      challenge: base64ToArrayBuffer(options.challenge),
      allowCredentials: options.allowCredentials.map(cred => ({
        ...cred,
        id: base64ToArrayBuffer(cred.id)
      }))
    };
    
    // Step 3: Request credential from authenticator
    const credential = await navigator.credentials.get({
      publicKey: publicKeyCredentialRequestOptions
    });
    
    // Step 4: Prepare credential for server
    const credentialJSON = {
      id: arrayBufferToBase64(credential.rawId),
      rawId: arrayBufferToBase64(credential.rawId),
      response: {
        clientDataJSON: arrayBufferToBase64(credential.response.clientDataJSON),
        authenticatorData: arrayBufferToBase64(credential.response.authenticatorData),
        signature: arrayBufferToBase64(credential.response.signature),
        userHandle: credential.response.userHandle ? 
          arrayBufferToBase64(credential.response.userHandle) : null
      },
      type: credential.type
    };
    
    // Step 5: Send credential to server for verification
    const verifyResponse = await fetch('/auth/passkey/verify/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username,
        credential: credentialJSON
      })
    });
    
    if (!verifyResponse.ok) {
      const error = await verifyResponse.json();
      throw new Error(error.message);
    }
    
    const { access, refresh, is_admin } = await verifyResponse.json();
    
    // Step 6: Store tokens
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
    
    return { success: true, is_admin };
    
  } catch (error) {
    console.error('Passkey authentication failed:', error);
    return { success: false, error: error.message };
  }
}

// Helper functions
function base64ToArrayBuffer(base64) {
  const binaryString = atob(base64.replace(/-/g, '+').replace(/_/g, '/'));
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes.buffer;
}

function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary)
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '');
}
```

### React Example

```jsx
import { useState } from 'react';

function PasskeyLogin() {
  const [username, setUsername] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handlePasskeyLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const result = await loginWithPasskey(username);
    
    if (result.success) {
      // Redirect to dashboard or home
      window.location.href = result.is_admin ? '/admin' : '/dashboard';
    } else {
      setError(result.error);
    }
    
    setLoading(false);
  };

  return (
    <form onSubmit={handlePasskeyLogin}>
      <input
        type="text"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        placeholder="Username"
        required
      />
      <button type="submit" disabled={loading}>
        {loading ? 'Authenticating...' : 'Login with Passkey'}
      </button>
      {error && <p className="error">{error}</p>}
    </form>
  );
}
```

---

## Important Notes

1. **HTTPS Required**: Passkey authentication requires HTTPS in production (localhost is allowed for development).

2. **Browser Support**: Passkeys are supported in:
   - Chrome/Edge 67+
   - Firefox 60+
   - Safari 13+

3. **Credential Storage**: Passkey credentials are stored in the `PasskeyCredential` model:
   - Users can have multiple passkeys (different devices)
   - Each credential has a unique ID
   - Sign count is tracked to prevent replay attacks

4. **Challenge Expiration**: Authentication challenges expire after 5 minutes for security.

5. **User Verification**: Set to "preferred" - uses biometric/PIN if available, but not required.

6. **RP ID (Relying Party ID)**: Automatically set to your domain name without port.

---

## Security Considerations

- Challenges are stored in cache with 5-minute expiration
- Each credential has a sign counter to detect cloned authenticators
- Credentials are scoped to specific users
- Public key cryptography ensures credentials cannot be phished
- User verification (biometric/PIN) provides additional security layer

---

## Testing

To test passkey authentication:

1. Register a passkey for a test user (registration endpoint not shown in this doc - would need to be implemented separately)
2. Use a device with biometric authentication (Face ID, Touch ID, Windows Hello) or a hardware security key
3. Test the login flow with the provided frontend code
4. Verify JWT tokens are issued correctly

---

## Troubleshooting

**"No passkeys registered for this user"**
- User needs to register a passkey first (requires passkey registration endpoint)

**"Challenge expired or not found"**
- Request a new challenge by calling the `/auth/passkey/challenge/` endpoint again

**"Authentication failed"**
- Verify the credential response format matches the expected structure
- Check that the RP ID matches your domain
- Ensure HTTPS is used in production

