"""
Wspólny moduł aplikacji Mundial Typer 2026.

Zawiera logikę używaną zarówno przez stronę główną (app.py), jak i przez
podstrony w katalogu pages/ (Terminarz, Statystyki): połączenie z Supabase,
ładowanie i normalizację danych, punktację, pomocnicze funkcje czasu,
wspólny motyw CSS oraz strażnika logowania.

UWAGA: ten moduł NIE wykonuje żadnych komend Streamlit na poziomie importu
(tylko definicje), więc można go bezpiecznie importować przed st.set_page_config.
"""

import os
from datetime import datetime

import streamlit as st
import pandas as pd
import pytz
from supabase import create_client


# --- Lista typerów (jedyne źródło prawdy; app.py i podstrony importują stąd) ---
LISTA_TYPEROW = [
    "Kamil Kiwer", "Jakub Szabat", "Bartosz Jarzyński", "Mateusz Panic",
    "Jakub Michalczyk", "Bartek Michalczyk", "Fabian Gołębiowski",
    "Piotr Strusz", "Michał Kruczalok",
]

POLAND_TZ = pytz.timezone("Europe/Warsaw")


# --- Połączenie z Supabase ---
@st.cache_resource
def get_supabase_client():
    """Ustanawia połączenie z Supabase (st.secrets['supabase'] lub zmienne środowiskowe)."""
    try:
        url = None
        key = None
        if "supabase" in st.secrets:
            sb = st.secrets["supabase"]
            url = sb.get("url")
            key = sb.get("anon_key") or sb.get("key")
        url = url or os.getenv("SUPABASE_URL")
        key = key or os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("Brak url/key w konfiguracji Supabase.")
        return create_client(url, key)
    except Exception as e:
        st.error(f"Błąd połączenia z Supabase: {e}")
        return None


# --- Normalizacja kolumn z Supabase ---
EXPECTED_MAP_MATCHES = {
    "id": ["id", "matchid", "match_id"],
    "home": ["home", "home_team", "hometeam"],
    "away": ["away", "away_team", "awayteam"],
    "homeGoals": ["homeGoals", "home_goals", "homegoals"],
    "awayGoals": ["awayGoals", "away_goals", "awaygoals"],
}

EXPECTED_MAP_PREDICTIONS = {
    "name": ["name", "player", "username"],
    "matchId": ["matchId", "match_id", "matchid", "id"],
    "homeGoals": ["homeGoals", "home_goals", "homegoals"],
    "awayGoals": ["awayGoals", "away_goals", "awaygoals"],
}


def _normalize_columns(df, expected_map):
    """Ujednolica nazwy kolumn i dodaje brakujące jako NaN."""
    if df is None or df.empty:
        return pd.DataFrame(columns=list(expected_map.keys()))

    cols_norm = {c: "".join(ch for ch in c.lower() if ch.isalnum()) for c in df.columns}
    rename_map = {}
    for desired, variants in expected_map.items():
        for v in variants:
            v_norm = "".join(ch for ch in v.lower() if ch.isalnum())
            found = next((orig for orig, norm in cols_norm.items() if norm == v_norm), None)
            if found:
                rename_map[found] = desired
                break
    df = df.rename(columns=rename_map)
    for desired in expected_map.keys():
        if desired not in df.columns:
            df[desired] = pd.NA
    return df


@st.cache_data(ttl=10)
def load_data():
    """Ładuje i normalizuje tabele `matches` i `predictions` z Supabase."""
    client = get_supabase_client()
    if client is None:
        return pd.DataFrame(), pd.DataFrame()
    try:
        res_m = client.table("matches").select("*").execute()
        df_mecze = pd.DataFrame(res_m.data if hasattr(res_m, "data") else res_m)
        res_p = client.table("predictions").select("*").execute()
        df_typy = pd.DataFrame(res_p.data if hasattr(res_p, "data") else res_p)
    except Exception as e:
        st.error(f"Błąd podczas ładowania danych z Supabase: {e}")
        return pd.DataFrame(), pd.DataFrame()

    df_mecze = _normalize_columns(df_mecze, EXPECTED_MAP_MATCHES)
    df_typy = _normalize_columns(df_typy, EXPECTED_MAP_PREDICTIONS)
    if not df_mecze.empty:
        df_mecze["id"] = df_mecze["id"].astype(int)
    if not df_typy.empty:
        if "matchId" in df_typy.columns:
            df_typy["id"] = df_typy["matchId"].astype(int)
        elif "id" in df_typy.columns:
            df_typy["id"] = df_typy["id"].astype(int)
    return df_mecze, df_typy


# --- Czas i formatowanie ---
def get_poland_time():
    """Bieżący czas w strefie Europe/Warsaw."""
    return datetime.now(POLAND_TZ)


def parse_match_time(start_time_str):
    """Parsuje start_time meczu do tz-aware datetime (Europe/Warsaw) lub None."""
    if pd.isna(start_time_str) or str(start_time_str).strip() == "":
        return None
    match_time = None
    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M"]:
        try:
            match_time = datetime.strptime(str(start_time_str).strip(), fmt)
            break
        except ValueError:
            continue
    if match_time is None:
        try:
            match_time = pd.to_datetime(start_time_str).to_pydatetime()
        except Exception:
            return None
    if match_time.tzinfo is None:
        match_time = POLAND_TZ.localize(match_time)
    else:
        match_time = match_time.astimezone(POLAND_TZ)
    return match_time


def has_match_started(start_time_str):
    """True, jeśli mecz już się rozpoczął względem czasu polskiego."""
    mt = parse_match_time(start_time_str)
    if mt is None:
        return False
    return get_poland_time() >= mt


def ma_wartosc(v):
    """True, jeśli pole wyniku jest wypełnione."""
    return not (pd.isna(v) or str(v).strip() == "")


def format_wynik(hg, ag):
    """Formatuje parę goli jako 'X-Y' lub '—' przy braku danych."""
    try:
        return f"{int(float(hg))}-{int(float(ag))}"
    except Exception:
        return "—"


# --- Punktacja ---
def oblicz_punkty(tg, tk, wg, wk):
    """Zwraca punkty za typ: 3 = dokładny wynik, 1 = trafiony rezultat, 0 = pudło."""
    if tg == wg and tk == wk:
        return 3
    if (tg > tk and wg > wk) or (tg < tk and wg < wk) or (tg == tk and wg == wk):
        return 1
    return 0


def kategoria_typu(tg, tk, wg, wk):
    """Zwraca etykietę trafienia: 'dokladny' | 'zwyciezca' | 'pudlo'."""
    pkt = oblicz_punkty(tg, tk, wg, wk)
    return {3: "dokladny", 1: "zwyciezca", 0: "pudlo"}[pkt]


# Wspólna mapa stylów dla kategorii trafień (używana w tabelach z kolorami).
KOLORY_KATEGORII = {
    "dokladny":  "background-color: rgba(34,197,94,0.45); color:#eafff1; font-weight:600;",
    "zwyciezca": "background-color: rgba(249,115,22,0.45); color:#fff4e8; font-weight:600;",
    "pudlo":     "background-color: rgba(239,68,68,0.40); color:#ffecec;",
    "brak":      "color:#6b7280;",
    "":          "",
}


# --- Strażnik logowania dla podstron ---
def require_login():
    """Zatrzymuje renderowanie podstrony, jeśli użytkownik nie jest zalogowany."""
    if st.session_state.get("logged_in_user") is None:
        st.warning("🔒 Zaloguj się na stronie głównej (**Mundial Typer**), aby zobaczyć tę zakładkę.")
        st.stop()


# --- Wspólny motyw (futurystyczny, ciemny + neon) ---
def inject_custom_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Rajdhani:wght@400;500;600;700&display=swap');
        .stApp {
            background:
                radial-gradient(1200px 600px at 8% -10%, rgba(0,229,255,0.10), transparent 60%),
                radial-gradient(1000px 520px at 92% 8%, rgba(168,85,247,0.12), transparent 55%),
                linear-gradient(180deg, #070b16 0%, #0a0e1a 55%, #070a13 100%);
            background-attachment: fixed;
            color: #e8eefc;
        }
        html, body, [class*="css"] { font-family: 'Rajdhani', sans-serif; }
        h1, h2, h3 { font-family: 'Orbitron', sans-serif !important; letter-spacing: 1px; }
        h1 { color: #7df9ff !important; text-shadow: 0 0 18px rgba(0,229,255,0.45), 0 0 42px rgba(168,85,247,0.25); }
        h2, h3 { color: #cfe9ff !important; text-shadow: 0 0 16px rgba(0,229,255,0.18); }
        .stButton > button, [data-testid="stForm"] button {
            font-family: 'Rajdhani', sans-serif; font-weight: 700; text-transform: uppercase;
            letter-spacing: 1px; color: #04111c;
            background: linear-gradient(135deg, #00e5ff 0%, #36b9ff 100%);
            border: 1px solid rgba(0,229,255,0.6); border-radius: 12px; padding: 0.5rem 1.1rem;
            box-shadow: 0 0 18px rgba(0,229,255,0.30); transition: all .2s ease;
        }
        .stButton > button:hover, [data-testid="stForm"] button:hover {
            transform: translateY(-2px); box-shadow: 0 0 28px rgba(0,229,255,0.60); filter: brightness(1.08);
        }
        [data-testid="stForm"] {
            background: rgba(18,24,41,0.65); border: 1px solid rgba(0,229,255,0.25);
            border-radius: 18px; padding: 1.6rem 1.6rem 1.1rem;
            box-shadow: 0 8px 40px rgba(0,0,0,0.45), inset 0 0 0 1px rgba(255,255,255,0.03);
        }
        .stTextInput input:focus { border-color: #00e5ff !important; box-shadow: 0 0 0 2px rgba(0,229,255,0.30) !important; }
        [data-testid="stDataFrame"] {
            border: 1px solid rgba(0,229,255,0.25); border-radius: 14px; overflow: hidden;
            box-shadow: 0 0 24px rgba(0,229,255,0.12);
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(12,17,30,0.96), rgba(8,11,20,0.96));
            border-right: 1px solid rgba(0,229,255,0.18);
        }
        [data-testid="stAlert"] { border-radius: 12px; }
        [data-testid="stMetricValue"] { color: #7df9ff; font-family: 'Orbitron', sans-serif; }
        hr { border-color: rgba(0,229,255,0.20); }
        </style>
        """,
        unsafe_allow_html=True,
    )
