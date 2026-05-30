# Supabase Integration Setup Guide

## Overview
The World Cup Predictor app now uses Supabase to store `matches` and `predictions` tables.

## Setup Steps

### 1. Install Dependencies

First, install all required Python packages:

```bash
cd /Users/bartoszjarzynski/Desktop/vscode/worldCupPredictor
python3 -m pip install -r requirements.txt
```

### 2. Create a Supabase Project

1. Go to https://app.supabase.com and create a new project (or use an existing one).
2. In the project, create two tables (`matches` and `predictions`) with the schemas described below.

### 3. Configure `.streamlit/secrets.toml`

1. Open the file `.streamlit/secrets.toml` in the worldCupPredictor folder
2. Fill in the `url` and `anon_key` values from your Supabase project's API settings
3. Save the file

Example:
```toml
[supabase]
url = "https://your-project-ref.supabase.co"
anon_key = "YOUR_ANON_KEY"
```

### 4. Create Tables and Columns in Supabase

Create the following tables and columns (Postgres types shown in parentheses):

**Table: `matches`**
- `id` (integer) - primary key
- `home` (text)
- `away` (text)
- `homeGoals` (integer, nullable)
- `awayGoals` (integer, nullable)

**Table: `predictions`**
- `id` (integer) - match id (not necessarily primary key in this table)
- `name` (text)
- `homeGoals` (integer, nullable)
- `awayGoals` (integer, nullable)

Note: In `predictions` the combination of `name`+`id` should be treated as a unique key for a user's prediction for a match. You can create a unique constraint on (`name`, `id`) in Supabase/PG for data integrity.

### 5. Run the App

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## Troubleshooting

### "ModuleNotFoundError: No module named 'supabase'"
- Solution: Run `python3 -m pip install -r requirements.txt`

### "401 Unauthorized" or "Permission Denied"
- Make sure `url` and `anon_key` in `.streamlit/secrets.toml` are correct
- If using a service role key, be careful to not expose it in client contexts

### "Table not found"
- Verify you created `matches` and `predictions` with the exact names and columns described above

### Secrets Not Found
- Ensure `.streamlit/secrets.toml` exists in the project directory
- Make sure it's in the `.streamlit/` folder (not the root folder)

## Security Notes

⚠️ **NEVER commit `.streamlit/secrets.toml` to version control!**

For production deployment (like Streamlit Cloud), use the Secrets management in your deployment platform instead of a local file.

## How Scoring Works

- **3 points**: Exact score match (e.g., predicted 2-1, actual was 2-1)
- **1 point**: Correct winner/loser or tie
- **0 points**: Wrong winner/loser or incorrect tie prediction
