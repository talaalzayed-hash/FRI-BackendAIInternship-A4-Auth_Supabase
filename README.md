# Authentication API — Supabase + FastAPI

A small, secure REST API that handles user **sign up**, **log in** and **log out**, and
**protects** routes so they answer only for authenticated users.

Supabase is the Identity Provider: it stores the accounts, hashes the passwords and signs
the tokens. This API never stores a password and never hashes anything itself — it
*receives* a token, *verifies* it with Supabase, and opens or refuses the door.

---

## How it works

Authentication here is a trust triangle between three parties. Nobody trusts a plain
password sitting on the API server; instead Supabase vouches for the user by signing a
token, and this server checks that signature on every protected request.

| Step | Who | What happens |
|------|-----|--------------|
| 1. Sign up / Log in | client → this API → Supabase | Credentials are forwarded to Supabase, never stored here |
| 2. The token | Supabase → client | Supabase returns a signed **JWT** (the access token) |
| 3. The request | client → this API | The client calls a protected route with `Authorization: Bearer <token>` |
| 4. Verification | this API → Supabase | The server asks Supabase "is this token real?" — if yes, the door opens |

Step 4 is a real network call to Supabase (`supabase.auth.get_user(token)`), not a local
guess, which is what makes the answer trustworthy. A token that is expired, tampered with
or was never issued fails it.

---

## Tech stack

| | |
|---|---|
| Language | Python 3.12 |
| Framework | FastAPI |
| Server | Uvicorn |
| Identity Provider | Supabase Auth |
| Config | python-dotenv (`.env`) |
| Docs | Swagger UI (built in, at `/docs`) |

---

## Project structure

```
authentication-supabase-api/
├── app/
│   ├── main.py              # app instance, router wiring, AuthError handler
│   ├── schemas.py           # request body model (email + password)
│   ├── security.py          # THE GUARD — token extraction, verification, dependency
│   ├── database/
│   │   └── database.py      # Supabase client, built from .env
│   └── routers/
│       ├── auth.py          # /auth/signup, /auth/login, /auth/logout
│       ├── protected.py     # /protected/profile
│       └── public.py        # /public/info
├── .env                     # your secrets — git-ignored, never committed
├── .gitignore
└── README.md
```

All authentication logic lives in **one file**, `app/security.py`. The routers contain no
token-checking code at all — they declare `Depends(get_current_user)` and the guard runs
before the handler body is ever entered.

---

## Setup

### 1. Prerequisites

- Python 3.12+
- A free [Supabase](https://supabase.com) account — no credit card required

### 2. Create the Supabase project

1. Create a new project in the Supabase dashboard.
2. Open **Project Settings → API** and copy two values:
   - **Project URL**
   - **anon public key** — the key that is safe to use from a client.
     **Never use the `service_role` key here**; it bypasses all security.
3. Open **Authentication → Sign In / Providers → Email** and turn **"Confirm email" off**.

   Without this, every signup tries to send a confirmation email, and Supabase's built-in
   mail service allows only **2 emails per hour**, so your third test signup fails with
   `email rate limit exceeded`. With confirmation off, no mail is sent and a fresh account
   can log in immediately. (In production you would leave it on — email confirmation is a
   real security feature.)

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
SUPABASE_URL=your_project_url
SUPABASE_KEY=your_anon_key
```

`.env` is listed in `.gitignore` and must never be committed — bots scrape public repos
for leaked keys within minutes of a push.

### 4. Install and run

```bash
# create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# install dependencies
pip install fastapi uvicorn supabase python-dotenv

# run
uvicorn app.main:app --reload
```

The API is now at **http://localhost:8000**, and the interactive docs at
**http://localhost:8000/docs**.

---

## API reference

| Method | Route | Auth required | Success | Failure |
|--------|-------|---------------|---------|---------|
| `GET`  | `/` | no | `200` service is running | — |
| `GET`  | `/public/info` | no | `200` public message | — |
| `POST` | `/auth/signup` | no | `201` created user | `400` missing fields / Supabase rejection |
| `POST` | `/auth/login` | no | `200` access + refresh token | `400` missing fields · `401` bad credentials |
| `POST` | `/auth/logout` | **yes** — `Bearer <token>` | `204` no content | `401` missing or invalid token |
| `GET`  | `/protected/profile` | **yes** — `Bearer <token>` | `200` id, email, created_at | `401` missing or invalid token |

Every error response uses the same shape:

```json
{ "error": "Invalid or expired token" }
```

There are two distinct 401 messages, on purpose:

- `Access token required` — you presented nothing.
- `Invalid or expired token` — you presented something, and it is not genuine.

The second never says *why* it failed (expired vs. tampered vs. unknown), because that
would only help an attacker tune the next attempt.

---

## Example requests

**Sign up**

```bash
curl -i -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
# 201 Created
```

**Log in — returns the token**

```bash
curl -i -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": { "...": "..." }
}
```

**Read the protected profile**

```bash
curl -i http://localhost:8000/protected/profile \
  -H "Authorization: Bearer PASTE_ACCESS_TOKEN_HERE"
```

```json
{
  "id": "0f8c...-...-...",
  "email": "test@example.com",
  "created_at": "2026-09-01T10:22:31.512Z"
}
```

Change any single character of that token and run it again — the response becomes
`401 {"error": "Invalid or expired token"}`. That is a forged pass being rejected.

**Log out**

```bash
curl -i -X POST http://localhost:8000/auth/logout \
  -H "Authorization: Bearer PASTE_ACCESS_TOKEN_HERE"
# 204 No Content
```

---

## Using Swagger UI

Open **http://localhost:8000/docs**. Protected routes show a padlock icon.

1. Run `POST /auth/login` and copy the `access_token` value from the response.
2. Click **Authorize** (top right) and paste **just the token** — no `Bearer ` prefix.
   Swagger adds the scheme itself; typing it produces `Bearer Bearer <token>` and a 401.
3. Click Authorize, then Close. The padlocks close.
4. Run `GET /protected/profile` → **Try it out** → **Execute** → `200`.

> **Note:** OpenAPI forbids documenting `Authorization` as an ordinary header parameter —
> Swagger silently drops such a field and never sends it. That is why this project declares
> a proper `HTTPBearer` security scheme instead; it is what makes the **Authorize** button
> appear and actually transmit the header.

### Screenshot

![Swagger UI showing the Authorize padlock and the protected profile route](docs/swagger.png)

*(Replace with your own screenshot: take one of `/docs` after authorizing, showing the
padlocks and a successful `200` from `/protected/profile`.)*

---

## The guard

`app/security.py` holds a single FastAPI dependency, `get_current_user`, used by every
protected route:

```python
@router.get("/profile")
def profile(current_user: CurrentUser = Depends(get_current_user)):
    return current_user.public_profile()
```

That is the whole handler. Protecting a new route means adding that one parameter — no
authentication code is copied, so no door can be left unguarded by forgetting to paste
the check in.

The guard **raises** on failure rather than returning an error. A dependency that returns
a value is treated as a success and hands that value to the route, so raising is what
guarantees the handler body is never entered by an unverified caller. `main.py` converts
the raised `AuthError` into the standard `{"error": "..."}` response.

Successful responses return **safe metadata only** — id, email, created date. Never the
token, the session, or `app_metadata`.

---

## Security notes

- **`.env` is never committed.** Only `SUPABASE_URL` and the **anon** key belong in it.
- **The `service_role` key is not used anywhere** in this project. It bypasses every
  security rule and must never reach client-side code or a public repository.
- **Passwords are never stored or hashed here.** They are forwarded to Supabase and
  forgotten. Rolling your own password hashing is how security incidents start.
- **Login failures are deliberately vague** (`Invalid login credentials`) so an attacker
  cannot learn which half of the pair was wrong, or which emails are registered.
- **Logout has a real limitation worth understanding.** JWTs are *stateless*: the server
  holds no session to destroy, so an already-issued access token keeps working until it
  expires (one hour by default). `POST /auth/logout` ends the Supabase session, but
  instant, guaranteed revocation would need a token blocklist or much shorter token
  lifetimes. This is the trade-off that makes stateless auth fast and horizontally
  scalable — and it is why refresh tokens exist.

---

## Known limitations / next steps

- `PORT` is present in `.env` but the app does not read it; the port comes from the
  `uvicorn --port` flag. Either wire it up or drop the variable.
- No automated test suite yet — the endpoints have been verified manually and with curl.
- No rate limiting on `/auth/login`, so brute-force protection currently relies on
  Supabase's own limits.
