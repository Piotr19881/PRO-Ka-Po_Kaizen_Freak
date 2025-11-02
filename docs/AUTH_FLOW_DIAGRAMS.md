# Authentication Flow Diagrams

## 1. Registration Flow

```
┌─────────────┐                  ┌─────────────┐                  ┌─────────────┐
│   Desktop   │                  │   FastAPI   │                  │  PostgreSQL │
│     App     │                  │     API     │                  │   Database  │
└──────┬──────┘                  └──────┬──────┘                  └──────┬──────┘
       │                                │                                │
       │ POST /api/v1/auth/register     │                                │
       │ {email, password, name, ...}   │                                │
       ├───────────────────────────────>│                                │
       │                                │                                │
       │                                │ Check if email exists          │
       │                                ├───────────────────────────────>│
       │                                │<───────────────────────────────┤
       │                                │                                │
       │                                │ Hash password (bcrypt)         │
       │                                │                                │
       │                                │ INSERT INTO users              │
       │                                ├───────────────────────────────>│
       │                                │<───────────────────────────────┤
       │                                │                                │
       │                                │ INSERT INTO user_profiles      │
       │                                ├───────────────────────────────>│
       │                                │<───────────────────────────────┤
       │                                │                                │
       │                                │ Generate 6-digit code          │
       │                                │                                │
       │                                │ INSERT INTO verification_tokens│
       │                                ├───────────────────────────────>│
       │                                │<───────────────────────────────┤
       │                                │                                │
       │                                │ Send verification email        │
       │                                │ (Gmail SMTP)                   │
       │                                │                                │
       │ {success: true, user_id, ...}  │                                │
       │<───────────────────────────────┤                                │
       │                                │                                │
       │                                                                  
       │ User checks email              ┌─────────────┐                  
       │ Receives: 123456               │    Gmail    │                  
       │<───────────────────────────────┤   Server    │                  
       │                                └─────────────┘                  
       │                                                                  
       │ POST /api/v1/auth/verify-email │                                │
       │ {email, code: "123456"}        │                                │
       ├───────────────────────────────>│                                │
       │                                │                                │
       │                                │ SELECT FROM verification_tokens│
       │                                ├───────────────────────────────>│
       │                                │<───────────────────────────────┤
       │                                │                                │
       │                                │ Validate code & expiry         │
       │                                │                                │
       │                                │ UPDATE users.email_verified    │
       │                                ├───────────────────────────────>│
       │                                │<───────────────────────────────┤
       │                                │                                │
       │                                │ DELETE verification_token      │
       │                                ├───────────────────────────────>│
       │                                │<───────────────────────────────┤
       │                                │                                │
       │                                │ Create JWT tokens              │
       │                                │                                │
       │ {access_token, refresh_token}  │                                │
       │<───────────────────────────────┤                                │
       │                                │                                │
       │ Store tokens in keyring        │                                │
       │ Redirect to main app           │                                │
       │                                │                                │
```

## 2. Login Flow

```
┌─────────────┐                  ┌─────────────┐                  ┌─────────────┐
│   Desktop   │                  │   FastAPI   │                  │  PostgreSQL │
│     App     │                  │     API     │                  │   Database  │
└──────┬──────┘                  └──────┬──────┘                  └──────┬──────┘
       │                                │                                │
       │ POST /api/v1/auth/login        │                                │
       │ {email, password}              │                                │
       ├───────────────────────────────>│                                │
       │                                │                                │
       │                                │ SELECT FROM users WHERE email  │
       │                                ├───────────────────────────────>│
       │                                │<───────────────────────────────┤
       │                                │                                │
       │                                │ Verify password (bcrypt)       │
       │                                │                                │
       │                                │ Check email_verified != NULL   │
       │                                │                                │
       │                                │ Create JWT tokens              │
       │                                │                                │
       │ {access_token, refresh_token,  │                                │
       │  user: {id, email, name, ...}} │                                │
       │<───────────────────────────────┤                                │
       │                                │                                │
       │ Store tokens in keyring        │                                │
       │ Load user preferences          │                                │
       │ Apply theme & language         │                                │
       │ Show main window               │                                │
       │                                │                                │
```

## 3. Password Reset Flow

```
┌─────────────┐                  ┌─────────────┐                  ┌─────────────┐
│   Desktop   │                  │   FastAPI   │                  │  PostgreSQL │
│     App     │                  │     API     │                  │   Database  │
└──────┬──────┘                  └──────┬──────┘                  └──────┬──────┘
       │                                │                                │
       │ POST /api/v1/auth/forgot-password                               │
       │ {email, language}              │                                │
       ├───────────────────────────────>│                                │
       │                                │                                │
       │                                │ SELECT FROM users WHERE email  │
       │                                ├───────────────────────────────>│
       │                                │<───────────────────────────────┤
       │                                │                                │
       │                                │ Generate 6-digit code          │
       │                                │                                │
       │                                │ DELETE old reset tokens        │
       │                                ├───────────────────────────────>│
       │                                │<───────────────────────────────┤
       │                                │                                │
       │                                │ INSERT INTO verification_tokens│
       │                                │ (identifier: "reset_email")    │
       │                                ├───────────────────────────────>│
       │                                │<───────────────────────────────┤
       │                                │                                │
       │                                │ Send password reset email      │
       │                                │ (Gmail SMTP)                   │
       │                                │                                │
       │ {success: true, message}       │                                │
       │<───────────────────────────────┤                                │
       │                                │                                │
       │                                                                  
       │ User checks email              ┌─────────────┐                  
       │ Receives: 654321               │    Gmail    │                  
       │<───────────────────────────────┤   Server    │                  
       │                                └─────────────┘                  
       │                                                                  
       │ POST /api/v1/auth/reset-password                                │
       │ {email, code: "654321",        │                                │
       │  new_password}                 │                                │
       ├───────────────────────────────>│                                │
       │                                │                                │
       │                                │ SELECT FROM verification_tokens│
       │                                │ WHERE identifier="reset_email" │
       │                                ├───────────────────────────────>│
       │                                │<───────────────────────────────┤
       │                                │                                │
       │                                │ Validate code & expiry         │
       │                                │                                │
       │                                │ Hash new password (bcrypt)     │
       │                                │                                │
       │                                │ UPDATE users.password          │
       │                                ├───────────────────────────────>│
       │                                │<───────────────────────────────┤
       │                                │                                │
       │                                │ DELETE verification_token      │
       │                                ├───────────────────────────────>│
       │                                │<───────────────────────────────┤
       │                                │                                │
       │ {success: true, message}       │                                │
       │<───────────────────────────────┤                                │
       │                                │                                │
       │ Show success message           │                                │
       │ Return to login screen         │                                │
       │                                │                                │
```

## 4. Token Refresh Flow

```
┌─────────────┐                  ┌─────────────┐
│   Desktop   │                  │   FastAPI   │
│     App     │                  │     API     │
└──────┬──────┘                  └──────┬──────┘
       │                                │
       │ Access token expires (15 min)  │
       │                                │
       │ POST /api/v1/auth/refresh      │
       │ {refresh_token}                │
       ├───────────────────────────────>│
       │                                │
       │                                │ Decode & validate refresh token
       │                                │ Check expiry (7 days)
       │                                │ Verify token type = "refresh"
       │                                │
       │                                │ Extract user_id from token
       │                                │
       │                                │ Create new access token
       │                                │
       │ {access_token}                 │
       │<───────────────────────────────┤
       │                                │
       │ Update stored access token     │
       │ Continue normal operation      │
       │                                │
```

## 5. API Request with Authentication

```
┌─────────────┐                  ┌─────────────┐                  ┌─────────────┐
│   Desktop   │                  │   FastAPI   │                  │  PostgreSQL │
│     App     │                  │     API     │                  │   Database  │
└──────┬──────┘                  └──────┬──────┘                  └──────┬──────┘
       │                                │                                │
       │ GET /api/v1/tasks              │                                │
       │ Headers:                       │                                │
       │   Authorization: Bearer <token>│                                │
       ├───────────────────────────────>│                                │
       │                                │                                │
       │                                │ Decode & validate access token │
       │                                │ Extract user_id from token     │
       │                                │                                │
       │                                │ SELECT FROM tasks              │
       │                                │ WHERE user_id = <from_token>   │
       │                                ├───────────────────────────────>│
       │                                │<───────────────────────────────┤
       │                                │                                │
       │ {tasks: [...]}                 │                                │
       │<───────────────────────────────┤                                │
       │                                │                                │
```

## Security Features

### Password Storage
```
Plain Password → bcrypt.hashpw(password, salt) → $2b$12$... (stored in DB)
                                                    ↓
                                          Never stored in plain text
                                          Salt is unique per password
                                          Computationally expensive (slow brute force)
```

### JWT Token Structure
```
Access Token (15 min expiry):
{
  "sub": "user-uuid",      # User ID
  "email": "user@mail.com", # User email
  "exp": 1762036834,       # Expiration timestamp
  "type": "access"         # Token type
}

Refresh Token (7 days expiry):
{
  "sub": "user-uuid",      # User ID
  "exp": 1762639834,       # Expiration timestamp
  "type": "refresh"        # Token type
}
```

### Verification Code
```
Format: 6 digits (000000 - 999999)
Expiry: 15 minutes for email verification
        30 minutes for password reset
Storage: verification_tokens table
         identifier = email (verification) or "reset_email" (password reset)
         Deleted after successful use
```

## Error Handling

### Common Errors
- **400 Bad Request**: Invalid data, expired code, email already exists
- **401 Unauthorized**: Invalid credentials, expired token
- **403 Forbidden**: Email not verified
- **404 Not Found**: User not found
- **500 Internal Server Error**: Database error, email sending failure

### Desktop App Should Handle
1. **Network errors**: Show "Cannot connect to server"
2. **Token expiry**: Auto-refresh or redirect to login
3. **Email not verified**: Show verification dialog
4. **Invalid credentials**: Show error message
5. **Code expiry**: Offer to resend code

## Token Storage (Desktop App)

### Recommended: System Keyring
```python
import keyring

# Store tokens after login
keyring.set_password("PRO-Ka-Po", "access_token", access_token)
keyring.set_password("PRO-Ka-Po", "refresh_token", refresh_token)

# Retrieve tokens for API calls
access_token = keyring.get_password("PRO-Ka-Po", "access_token")

# Delete tokens on logout
keyring.delete_password("PRO-Ka-Po", "access_token")
keyring.delete_password("PRO-Ka-Po", "refresh_token")
```

### Alternative: Encrypted File
- Use `cryptography` library
- Derive encryption key from machine UUID
- Store in user's AppData folder
- Never store in plain text!

---

**Note**: All diagrams represent the complete, tested, and functional authentication system.
