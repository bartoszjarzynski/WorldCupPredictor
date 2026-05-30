# Mundial Typer 2026

Streamlit app for saving World Cup predictions to Supabase and showing a live leaderboard.

## What this repo contains

- `app.py` - main Streamlit application
- `requirements.txt` - Python dependencies
- `.streamlit/secrets.toml` is ignored and should contain your Supabase credentials
- `SETUP_GUIDE.md` - setup instructions for Supabase integration

## Local setup

1. Create a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   python3 -m pip install -r requirements.txt
   ```

3. Create `.streamlit/secrets.toml` with your Supabase values:
   ```toml
   [supabase]
   url = "https://your-project-id.supabase.co"
   anon_key = "your-anon-public-api-key"
   ```

4. Run the app:
   ```bash
   streamlit run app.py
   ```
