# 🔐 Password Management Setup

## Overview

The app now uses **secure password hashing with bcrypt** stored in Supabase. No plain-text passwords are hardcoded or visible to anyone, including the developer.

**Key features:**
- ✅ Users can change their own passwords anytime
- ✅ Passwords are securely hashed (bcrypt)
- ✅ Even you (the developer) can't see users' passwords
- ✅ Each user controls their own security

## Setup Instructions

### Step 1: Create the `user_credentials` Table in Supabase

You need to create a new table in Supabase to store user credentials. Follow these steps:

1. Go to your **Supabase Dashboard**
2. Click on **SQL Editor** (or go to **Tables**)
3. Click **New Query** and run this SQL:

```sql
CREATE TABLE user_credentials (
  id BIGSERIAL PRIMARY KEY,
  username VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

4. Click **Run** to create the table

### Step 2: Install Updated Dependencies

Run this command in your terminal:

```bash
pip install -r requirements.txt
```

### Step 3: Initial Password Setup (For First Time Only)

The first time each user logs in, they need to set their password. You can either:

**Option A: Manual Setup** (Recommended for privacy)
- Each user sets their own password via the app's change password feature
- They don't need to know an initial password
- Share the app link and let them click "Zmień hasło" → "Zaloguj się"

**Option B: Admin Setup**
- As the organizer, you can pre-set initial passwords:

```python
# Run this in a Python terminal in your project:
import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

# Generate hashes for initial passwords
users = [
    "Kamil Kiwer",
    "Jakub Szabat",
    "Bartosz Jarzyński",
    "Mateusz Panic",
    "Jakub Michalczyk",
    "Bartek Michalczyk",
    "Fabian Gołębiowski",
    "Piotr Strusz",
    "Michał Kruczalok",
]

for user in users:
    initial_password = f"{user.lower().replace(' ', '')}123"  # Example: kamil123
    hashed = hash_password(initial_password)
    print(f"{user}: {hashed}")
```

Then manually insert these into Supabase:
- Go to **Supabase → Tables → user_credentials → Insert**
- Add username and password_hash for each user

### Step 4: How Users Change Passwords

Users can now change their passwords safely:

1. **Login** with any password (system will prompt if not set)
2. Click **"🔑 Zmień hasło"** in the sidebar
3. Enter current password, then new password twice
4. Click **"Zmień hasło"** to save

The password is:
- ✅ Encrypted with bcrypt
- ✅ Stored securely in Supabase
- ✅ Never visible to you or other users

## Security Best Practices

1. **Never hardcode passwords** - You've already removed them ✅
2. **Use HTTPS** - Deploy on Streamlit Cloud or similar ✅
3. **Keep bcrypt installed** - It's in requirements.txt ✅
4. **Let users manage passwords** - They should change them regularly
5. **No password recovery** - Users must contact you if they forget (you can reset from Supabase)

## Troubleshooting

### Error: "user_credentials table does not exist"
→ Create the table using the SQL above

### Error: "Bcrypt not found"
→ Run: `pip install bcrypt`

### User locked out
→ Manually delete their row from `user_credentials` table in Supabase
→ They can set a new password on next login

## Production Deployment

When deploying to **Streamlit Cloud**:

1. Go to your app settings
2. Add **Secrets**:
   ```
   [supabase]
   url = "https://your-project.supabase.co"
   anon_key = "your-anon-key"
   ```
3. The app will use these credentials automatically

Done! 🎉 Your app now has secure, user-managed passwords.
