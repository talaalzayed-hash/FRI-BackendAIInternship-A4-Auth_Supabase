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

## Swagger UI and results

FastAPI generates interactive documentation from the code itself. Start the server and
open **http://localhost:8000/docs** — every endpoint can be called straight from the page,
and protected routes show a padlock icon.

### Authorizing once

1. Run `POST /auth/login` and copy the `access_token` value from the response.
2. Click **Authorize** (top right) and paste **just the token** — no `Bearer ` prefix.
   Swagger adds the scheme itself; typing it produces `Bearer Bearer <token>` and a 401.
3. Click **Authorize**, then **Close**. The padlocks close and every protected call from
   now on carries the header automatically.

![The Authorize dialog](docs/screenshots/00-authorize.png)

> **Why a security scheme and not a header field?** The OpenAPI specification states that a
> header parameter named `Authorization` *"SHALL be ignored"*. Swagger obeys that literally:
> such a box is never transmitted, so every call looks like a missing token no matter what
> you type. This project therefore declares a proper `HTTPBearer` scheme — that is what
> makes the **Authorize** button appear and actually send the header.

---

### 1 · `POST /auth/signup` — create an account

No authentication. Returns `201` with the new user, or `400` if a field is missing or
Supabase rejects the credentials.

```bash
curl -i -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

```json
{
  "message": "User created",
  "user": { "id": "0f8c...", "email": "test@example.com", "...": "..." }
}
```

![Signup returning 201](docs/screenshots/01-signup.png)

---

### 2 · `POST /auth/login` — exchange credentials for a token

No authentication. Returns `200` with the signed JWT, or `401` for bad credentials.
This is where you get the token everything else needs.

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

![Login returning 200 and an access token](docs/screenshots/02-login.png)

---

### 3 · `GET /public/info` — the open lobby

No authentication, no token, no padlock. Anyone may call it.

```bash
curl -i http://localhost:8000/public/info
```

```json
{ "message": "Welcome stranger! This info is public." }
```

![Public info returning 200 without any token](docs/screenshots/03-public-info.png)

---

### 4 · `GET /protected/profile` — the locked door

Requires `Authorization: Bearer <token>`. Returns the caller's safe metadata.

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

![Protected profile returning 200 with a valid token](docs/screenshots/04-profile-200.png)

**Without a token** — nothing was presented:

```json
{ "error": "Access token required" }
```

![Protected profile returning 401 with no token](docs/screenshots/05-profile-401-no-token.png)

**With a forged token** — change any single character of a real token and call again.
Supabase checks the signature, so the edit is detected:

```json
{ "error": "Invalid or expired token" }
```

![Protected profile returning 401 for a tampered token](docs/screenshots/06-profile-401-forged.png)

The two 401 messages are deliberately different: *you showed me nothing* and *you showed me
something fake* are different facts about the request. The second never says **why** it
failed — expired, tampered with, or unknown — because that would only help an attacker
tune the next attempt.

---

### 5 · `POST /auth/logout` — end the session

Protected: it uses the same guard as `/protected/profile`. Returns `204 No Content` —
success with nothing to say, so the body is empty.

```bash
curl -i -X POST http://localhost:8000/auth/logout \
  -H "Authorization: Bearer PASTE_ACCESS_TOKEN_HERE"
# HTTP/1.1 204 No Content
```

![Logout returning 204](docs/screenshots/07-logout.png)

---

### The guard

Every protected route above is guarded by **one** function — `get_current_user` in
`app/security.py`. It extracts the token from the header, asks Supabase to verify it, and
hands the verified user to the route:

```python
@router.get("/profile")
def profile(current_user: CurrentUser = Depends(get_current_user)):
    return current_user.public_profile()
```

That is the entire handler. `app/routers/` contains no token-checking code at all.
Protecting a new route means adding that one parameter — nothing is copied, so no door can
be left unguarded by forgetting to paste the check in.

Three details that matter:

- **The guard raises, it does not return.** A dependency that returns a value is treated as
  a success and that value is handed to the route. Raising is what guarantees the handler
  body is never entered by an unverified caller. `main.py` turns the raised `AuthError`
  into the standard `{"error": "..."}` response.
- **Verification is a network call**, `supabase.auth.get_user(token)`, not a local guess.
  Supabase holds the signing key, so only Supabase can say for certain that a token is
  genuine and unexpired.
- **Only safe metadata comes back** — id, email, created date. Never the token, the
  session, or `app_metadata`.

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
