import os
import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
import json
import bcrypt
import hashlib
from datetime import datetime
import pytz

# Konfiguracja strony
st.set_page_config(page_title="Mundial Typer 2026", page_icon="⚽", layout="centered")

# --- KONFIGURACJA EKIPY ---
# Wpisz tutaj dokładnie 8 nicków Twoich znajomych
LISTA_TYPEROW = ["Kamil Kiwer", "Jakub Szabat", "Bartosz Jarzyński", "Mateusz Panic", "Jakub Michalczyk", "Bartek Michalczyk", "Fabian Gołębiowski", "Piotr Strusz", "Michał Kruczalok"]

# Inicjalizacja session state
if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None
if "auth_tried" not in st.session_state:
    st.session_state.auth_tried = False
if "show_password_change" not in st.session_state:
    st.session_state.show_password_change = False
if "show_setup_password" not in st.session_state:
    st.session_state.show_setup_password = False

# 1. Połączenie z Supabase
@st.cache_resource
def get_supabase_client():
    """Ustanawia połączenie z Supabase używając `st.secrets['supabase']` lub zmiennych środowiskowych."""
    try:
        url = None
        key = None

        if "supabase" in st.secrets:
            supabase_secrets = st.secrets["supabase"]
            url = supabase_secrets.get("url")
            key = supabase_secrets.get("anon_key") or supabase_secrets.get("key")

        url = url or os.getenv("SUPABASE_URL")
        key = key or os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")

        if not url or not key:
            raise ValueError(
                "Brakuje `url` lub `key` w konfiguracji Supabase. "
                "Ustaw `supabase` w secrets.toml lub zmienne środowiskowe SUPABASE_URL i SUPABASE_ANON_KEY."
            )

        client = create_client(url, key)
        return client
    except Exception as e:
        st.error(f"Błąd połączenia z Supabase: {e}")
        st.info(
            "W Streamlit Cloud dodaj tajne dane w ustawieniach aplikacji: "
            "https://streamlit.io/cloud/settings/secrets"
        )
        st.info(
            "Format:\n"
            "[supabase]\n"
            "url = \"https://your-project-id.supabase.co\"\n"
            "anon_key = \"your-anon-public-api-key\""
        )
        return None

# --- FUNKCJE BEZPIECZEŃSTWA HASEŁ ---
def hash_password(password: str) -> str:
    """Haszuje hasło używając bcrypt"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(stored_hash: str, password: str) -> bool:
    """Weryfikuje hasło z haszem"""
    try:
        return bcrypt.checkpw(password.encode(), stored_hash.encode())
    except:
        return False

def get_user_password_hash(username: str):
    """Pobiera zahaszowane hasło użytkownika z Supabase"""
    client = get_supabase_client()
    if client is None:
        return None
    
    try:
        result = client.table("user_credentials").select("password_hash").eq("username", username).execute()
        data = result.data if hasattr(result, "data") else result
        
        if data and len(data) > 0:
            return data[0].get("password_hash")
        return None
    except Exception as e:
        st.error(f"Błąd przy pobieraniu hasła: {e}")
        return None

def set_user_password(username: str, password: str) -> bool:
    """Ustawia lub aktualizuje hasło użytkownika w Supabase"""
    client = get_supabase_client()
    if client is None:
        return False
    
    try:
        password_hash = hash_password(password)
        
        # Sprawdzamy czy użytkownik już istnieje
        existing = client.table("user_credentials").select("username").eq("username", username).execute()
        existing_data = existing.data if hasattr(existing, "data") else existing
        
        if existing_data and len(existing_data) > 0:
            # Aktualizujemy istniejące hasło
            result = client.table("user_credentials").update({"password_hash": password_hash}).eq("username", username).execute()
        else:
            # Tworzymy nowy rekord
            result = client.table("user_credentials").insert({"username": username, "password_hash": password_hash}).execute()
        
        error = getattr(result, "error", None)
        if error:
            st.error(f"Błąd przy zapisywaniu hasła: {error}")
            return False
        return True
    except Exception as e:
        st.error(f"Błąd przy ustawianiu hasła: {e}")
        return False

def authenticate_user(username: str, password: str) -> bool:
    """Autentykuje użytkownika"""
    stored_hash = get_user_password_hash(username)
    if stored_hash is None:
        return False
    return verify_password(stored_hash, password)

def user_has_password(username: str) -> bool:
    """Sprawdza, czy użytkownik ma ustawione hasło"""
    return get_user_password_hash(username) is not None

def login_sidebar():
    """Wyświetla formularz logowania w sidebae"""
    with st.sidebar:
        st.write("---")
        st.subheader("🔐 Logowanie")
        
        username = st.selectbox("Wybierz swojego nicka:", LISTA_TYPEROW, key="login_user")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔑 Ustaw hasło", key="setup_pass_btn", help="Jeśli to Twoja pierwsza próba - kliknij tutaj"):
                st.session_state.show_setup_password = True
                st.rerun()
        with col2:
            if st.button("Zaloguj się", key="login_btn"):
                password = st.session_state.get("login_pass", "")
                if authenticate_user(username, password):
                    st.session_state.logged_in_user = username
                    st.session_state.auth_tried = True
                    st.success(f"Zalogowano jako: {username}")
                    st.rerun()
                else:
                    if not user_has_password(username):
                        st.error("Ten użytkownik nie ma jeszcze ustawionego hasła!")
                        st.info("Kliknij '🔑 Ustaw hasło' aby ustawić hasło.")
                    else:
                        st.error("Nieprawidłowe hasło!")
                    st.session_state.auth_tried = True
        
        password = st.text_input("Hasło:", type="password", key="login_pass")
        st.info("💡 Jeśli to Twoja pierwsza próba, kliknij '🔑 Ustaw hasło'")

def setup_password_dialog():
    """Wyświetla dialog do ustawienia hasła dla nowych użytkowników"""
    if st.session_state.show_setup_password:
        st.divider()
        st.subheader("🔑 Ustaw swoje hasło")
        st.info("Wybierz bezpieczne hasło, które będziesz pamiętać. Nikt inny go nie widzi!")
        
        with st.form("setup_password_form", clear_on_submit=False):
            username_for_setup = st.selectbox("Twój nick:", LISTA_TYPEROW, key="setup_user")
            new_password = st.text_input("Nowe hasło (min 6 znaków):", type="password", key="setup_new_pass")
            confirm_password = st.text_input("Potwierdź hasło:", type="password", key="setup_confirm_pass")
            
            col1, col2 = st.columns(2)
            with col1:
                submitted = st.form_submit_button("💾 Ustaw hasło")
            with col2:
                cancel = st.form_submit_button("❌ Anuluj")
            
            if cancel:
                st.session_state.show_setup_password = False
                st.rerun()
            
            if submitted:
                if not new_password or not confirm_password:
                    st.error("Wszystkie pola są wymagane!")
                elif new_password != confirm_password:
                    st.error("Hasła się nie zgadzają!")
                elif len(new_password) < 6:
                    st.error("Hasło musi mieć co najmniej 6 znaków!")
                elif user_has_password(username_for_setup):
                    st.error(f"Użytkownik {username_for_setup} ma już ustawione hasło!")
                    st.info("Aby zmienić hasło, zaloguj się i użyj opcji 'Zmień hasło'")
                else:
                    if set_user_password(username_for_setup, new_password):
                        st.success(f"✅ Hasło dla {username_for_setup} zostało ustawione!")
                        st.info("Teraz możesz się zalogować!")
                        st.session_state.show_setup_password = False
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Błąd przy ustawianiu hasła!")

def logout_sidebar():
    """Wyświetla przycisk wylogowania i opcje użytkownika w sidebae"""
    with st.sidebar:
        st.write("---")
        st.subheader(f"👤 {st.session_state.logged_in_user}")
        
        if st.button("🔑 Zmień hasło", key="change_pass_btn"):
            st.session_state.show_password_change = True
        
        if st.button("Wyloguj się", key="logout_btn"):
            st.session_state.logged_in_user = None
            st.session_state.auth_tried = False
            st.session_state.show_password_change = False
            st.rerun()

def show_password_change_dialog():
    """Wyświetla dialog do zmiany hasła"""
    if st.session_state.show_password_change:
        st.divider()
        st.subheader("🔑 Zmiana hasła")
        
        with st.form("change_password_form", clear_on_submit=False):
            old_password = st.text_input("Stare hasło:", type="password", key="old_pass")
            new_password = st.text_input("Nowe hasło:", type="password", key="new_pass")
            confirm_password = st.text_input("Potwierdź nowe hasło:", type="password", key="confirm_pass")
            
            submitted = st.form_submit_button("Zmień hasło")
            
            if submitted:
                if not old_password or not new_password or not confirm_password:
                    st.error("Wszystkie pola są wymagane!")
                elif new_password != confirm_password:
                    st.error("Nowe hasła się nie zgadzają!")
                elif len(new_password) < 6:
                    st.error("Nowe hasło musi mieć co najmniej 6 znaków!")
                elif not authenticate_user(st.session_state.logged_in_user, old_password):
                    st.error("Stare hasło jest nieprawidłowe!")
                else:
                    if set_user_password(st.session_state.logged_in_user, new_password):
                        st.success("✅ Hasło zostało zmienione!")
                        st.session_state.show_password_change = False
                        st.rerun()
                    else:
                        st.error("Błąd przy zmianie hasła!")

st.title("🏆 Oficjalny Typer Mundialu")
st.write("Wprowadzaj swoje typy i śledź tabelę na żywo!")

# --- SPRAWDZENIE LOGOWANIA ---
if st.session_state.logged_in_user is None:
    if st.session_state.show_setup_password:
        # Pokaż dialog do ustawienia hasła
        setup_password_dialog()
    else:
        # Pokaż formularz logowania
        login_sidebar()
    
    st.info("⚠️ Zaloguj się, aby uzyskać dostęp do aplikacji")
    st.stop()

# Użytkownik jest zalogowany - wyświetl opcję wylogowania
logout_sidebar()

# Wyświetl dialog do zmiany hasła jeśli użytkownik go otworzył
show_password_change_dialog()
def load_sheets_data():
    """Ładuje dane z Supabase tables: `matches` i `predictions`"""
    client = get_supabase_client()
    if client is None:
        return pd.DataFrame(), pd.DataFrame()

    try:
        # Pobierz wszystkie wiersze z tabeli matches
        res_matches = client.table("matches").select("*").execute()
        data_matches = res_matches.data if hasattr(res_matches, "data") else res_matches
        df_mecze = pd.DataFrame(data_matches)

        # Pobierz wszystkie wiersze z tabeli predictions
        res_preds = client.table("predictions").select("*").execute()
        data_preds = res_preds.data if hasattr(res_preds, "data") else res_preds
        df_typy = pd.DataFrame(data_preds)

        return df_mecze, df_typy
    except Exception as e:
        st.error(f"Błąd podczas ładowania danych z Supabase: {e}")
        return pd.DataFrame(), pd.DataFrame()

# Pobieranie danych
df_mecze, df_typy = load_sheets_data()


def _normalize_columns(df, expected_map):
    """Normalize column names in a DataFrame.

    expected_map: dict mapping desired_name -> list of possible variants
    The function will rename the first matching variant to desired_name.
    Missing desired columns will be created with NaN.
    """
    if df is None or df.empty:
        # create empty frame with expected columns
        cols = list(expected_map.keys())
        return pd.DataFrame(columns=cols)

    cols_lower = {c: ''.join(ch for ch in c.lower() if ch.isalnum()) for c in df.columns}
    rename_map = {}
    for desired, variants in expected_map.items():
        found = None
        for v in variants:
            v_norm = ''.join(ch for ch in v.lower() if ch.isalnum())
            for orig, norm in cols_lower.items():
                if norm == v_norm:
                    found = orig
                    break
            if found:
                break
        if found:
            rename_map[found] = desired
        else:
            # will create later as NaN
            pass

    df = df.rename(columns=rename_map)

    # Ensure all expected columns exist
    for desired in expected_map.keys():
        if desired not in df.columns:
            df[desired] = pd.NA

    return df


# Normalize common column name variations coming from Supabase
expected_map_matches = {
    "id": ["id", "matchid", "match_id"],
    "home": ["home", "home_team", "hometeam"],
    "away": ["away", "away_team", "awayteam"],
    "homeGoals": ["homeGoals", "home_goals", "homegoals", "home_goals"],
    "awayGoals": ["awayGoals", "away_goals", "awaygoals", "away_goals"],
}

expected_map_predictions = {
    "name": ["name", "player", "username"],
    "matchId": ["matchId", "match_id", "matchid", "id"],
    "homeGoals": ["homeGoals", "home_goals", "homegoals"],
    "awayGoals": ["awayGoals", "away_goals", "awaygoals"],
}

df_mecze = _normalize_columns(df_mecze, expected_map_matches)
df_typy = _normalize_columns(df_typy, expected_map_predictions)

# Upewniamy się, że typy danych są poprawne (baza potrafi wczytać liczby jako float/tekst)
if not df_mecze.empty:
    df_mecze["id"] = df_mecze["id"].astype(int)
if not df_typy.empty:
    # Normalize predictions table to use `id` as match id
    if "matchId" in df_typy.columns:
        df_typy["id"] = df_typy["matchId"].astype(int)
    elif "id" in df_typy.columns:
        df_typy["id"] = df_typy["id"].astype(int)

# --- FUNKCJE DO SPRAWDZENIA CZASU MECZU ---
def get_poland_time():
    """Pobiera bieżący czas w strefie czasowej Polski"""
    poland_tz = pytz.timezone('Europe/Warsaw')
    return datetime.now(poland_tz)

def has_match_started(start_time_str):
    """Sprawdza, czy mecz już się zaczął na podstawie czasu Polski"""
    if pd.isna(start_time_str) or str(start_time_str).strip() == "":
        return False
    
    try:
        # Parsuj czas meczu z różnych formatów
        match_time = None
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M"]:
            try:
                match_time = datetime.strptime(str(start_time_str).strip(), fmt)
                break
            except ValueError:
                continue
        
        if match_time is None:
            # Spróbuj parsować jako ISO format
            try:
                match_time = pd.to_datetime(start_time_str)
                match_time = match_time.to_pydatetime()
            except:
                return False
        
        # Jeśli czas nie ma info o strefie, zakładaj że to czas polski
        if match_time.tzinfo is None:
            poland_tz = pytz.timezone('Europe/Warsaw')
            match_time = poland_tz.localize(match_time)
        
        # Porównaj z bieżącym czasem w Polsce
        current_poland_time = get_poland_time()
        return current_poland_time >= match_time
    except Exception as e:
        st.warning(f"Błąd przy sprawdzaniu czasu meczu: {e}")
        return False

# --- SEKCJA 1: FORMULARZ TYPOWANIA ---
st.header("⚽ Obstaw mecz")

if df_mecze.empty:
    st.warning("Brak danych w tabeli 'matches' w Supabase — dodaj terminarz lub sprawdź polityki RLS.")
    st.info("Najczęstszą przyczyną pustych wyników przy poprawnym URL/kluczu jest włączone Row Level Security (RLS) bez polityki SELECT dla roli anon.")
    st.info(f"Pobrano wierszy: {0 if df_mecze is None else len(df_mecze)}")
    st.info("Kolumny pobrane z Supabase:")
    st.write(list(df_mecze.columns) if df_mecze is not None else "Brak ramki danych")
    st.write(df_mecze.head())
else:
    # Przygotowanie listy meczów do wyboru w formularzu
    # Pokazujemy tylko te mecze, które nie mają jeszcze wpisanego oficjalnego wyniku (czyli te, które można typować)
    def is_empty_score(value):
        return pd.isna(value) or str(value).strip() == ""

    home_empty = df_mecze["homeGoals"].apply(is_empty_score)
    away_empty = df_mecze["awayGoals"].apply(is_empty_score)
    mecze_bez_wyniku = df_mecze[home_empty | away_empty].sort_values("id")
    
    # Filtrujemy mecze, które jeszcze się nie zaczęły (na podstawie start_time i czasu Polski)
    if "start_time" in mecze_bez_wyniku.columns:
        mecze_do_typowania = mecze_bez_wyniku[~mecze_bez_wyniku["start_time"].apply(has_match_started)].sort_values("id")
        # Mecze, które już się zaczęły
        mecze_zakonczone = mecze_bez_wyniku[mecze_bez_wyniku["start_time"].apply(has_match_started)].sort_values("id")
    else:
        # Jeśli nie ma start_time, pokazujemy wszystkie mecze bez wyniku (wsteczna kompatybilność)
        mecze_do_typowania = mecze_bez_wyniku
        mecze_zakonczone = pd.DataFrame()

    if mecze_do_typowania.empty:
        if not mecze_zakonczone.empty:
            st.info("⏱️ Wszystkie dostępne mecze już się rozpoczęły. Nie możesz już typować.")
            st.subheader("Mecze w toku:")
            for _, mecz in mecze_zakonczone.iterrows():
                st.write(f"🔴 Mecz {int(mecz['id'])}: {mecz['home']} vs {mecz['away']}")
        else:
            st.info("Wszystkie mecze z zakładki 'Mecze' zostały już rozegrane i uzupełnione!")
    else:
        # Tworzymy ładny opis dla selectboxa, np. "Mecz 1: USA vs Maroko"
        mecze_do_typowania["Opis"] = mecze_do_typowania.apply(
            lambda r: f"Mecz {r['id']}: {r['home']} vs {r['away']}", axis=1
        )
        
        # Wyświetl komunikat o zagrożonych meczach
        if not mecze_zakonczone.empty:
            st.warning(f"⏱️ {len(mecze_zakonczone)} mecz(e) już się rozpoczął(y) - nie możesz typować.")
        
        with st.form("formularz_typu", clear_on_submit=False):
            # Zalogowany użytkownik nie musi wybierać nicka
            st.write(f"**Logowany jako:** {st.session_state.logged_in_user}")
            
            wybrany_mecz_opis = st.selectbox("Wybierz mecz:", mecze_do_typowania["Opis"])
            
            # Wyciągamy ID meczu z opisu
            wybrane_mecz_id = int(wybrany_mecz_opis.split(":")[0].split(" ")[1])
            
            col1, col2 = st.columns(2)
            with col1:
                gole_gospodarz = st.number_input("Gole Gospodarza:", min_value=0, step=1, value=0)
            with col2:
                gole_gosc = st.number_input("Gole Gościa:", min_value=0, step=1, value=0)
                
            submit_button = st.form_submit_button("Zapisz mój typ")
            
            if submit_button:
                # Używamy zalogowanego użytkownika
                wybrany_nick = st.session_state.logged_in_user
                
                # Sprawdzamy, czy ten użytkownik już typował ten mecz
                maska_duplikatu = (df_typy["name"] == wybrany_nick) & (df_typy["matchId"] == wybrane_mecz_id)
                
                # Tworzymy słownik dla obecnego typu
                record = {
                    "name": wybrany_nick,
                    "matchId": wybrane_mecz_id,
                    "homeGoals": gole_gospodarz,
                    "awayGoals": gole_gosc,
                }

                def save_prediction(record):
                    """Insert or update one prediction in Supabase."""
                    client = get_supabase_client()
                    if client is None:
                        return False, "Brak połączenia z Supabase."

                    try:
                        exists = client.table("predictions").select("*").eq("name", record["name"]).eq("matchId", record["matchId"]).execute()
                        if getattr(exists, "error", None):
                            return False, f"Błąd odczytu predictions: {exists.error}"

                        exists_data = exists.data if hasattr(exists, "data") else exists
                        if exists_data and len(exists_data) > 0:
                            res = client.table("predictions").update(record).match({"name": record["name"], "matchId": record["matchId"]}).execute()
                            action = "updated"
                        else:
                            res = client.table("predictions").insert(record).execute()
                            action = "inserted"

                        if getattr(res, "error", None):
                            return False, f"Błąd zapisu predictions: {res.error}"
                        return True, f"Dane zostały {action} w Supabase (predictions)."
                    except Exception as e:
                        return False, f"Błąd przy aktualizacji Supabase: {e}"

                ok, message = save_prediction(record)
                if ok:
                    if not df_typy.empty and maska_duplikatu.any():
                        df_typy.loc[maska_duplikatu, "homeGoals"] = gole_gospodarz
                        df_typy.loc[maska_duplikatu, "awayGoals"] = gole_gosc
                        st.success(f"Zaktualizowano Twój poprzedni typ na ten mecz!")
                    else:
                        nowy_wiersz = pd.DataFrame([record])
                        df_typy = pd.concat([df_typy, nowy_wiersz], ignore_index=True)
                        st.success(f"Twój typ został pomyślnie zapisany!")
                    st.success(message)
                    if hasattr(st, "experimental_rerun"):
                        st.experimental_rerun()
                else:
                    st.error(message)

# --- SEKCJA 2: TABELA WYNIKÓW (LEADERBOARD) ---
st.header("📊 Tabela Punktowa")

# Tworzymy bazową tabelę ze wszystkimi graczami (żeby każdy miał na start 0 punktów)
tabela_koncowa = pd.DataFrame({"name": LISTA_TYPEROW, "Punkty": 0}).set_index("name")

# Sprawdzamy, czy są jakiekolwiek typy i czy są wpisane jakieś oficjalne wyniki
df_wyniki_wpisane = df_mecze.dropna(subset=["homeGoals", "awayGoals"])
# Pozbywamy się też ewentualnych pustych stringów z bazy
df_wyniki_wpisane = df_wyniki_wpisane[(df_wyniki_wpisane["homeGoals"] != "") & (df_wyniki_wpisane["awayGoals"] != "")]

if df_typy.empty or df_wyniki_wpisane.empty:
    # Jeśli nikt nic nie typował lub nie ma wyników meczów, pokazujemy czystą tabelę z zerami
    st.dataframe(tabela_koncowa.reset_index(), use_container_width=True, hide_index=True)
    st.info("Punkty pojawią się, gdy zakończą się pierwsze mecze i uzupełnisz ich wyniki w Supabase.")
else:
    # Przygotowujemy kolumny wynikowe dla bezpiecznego łączenia
    df_typy_for_merge = df_typy.rename(columns={"homeGoals": "pred_homeGoals", "awayGoals": "pred_awayGoals"})
    df_wyniki_for_merge = df_wyniki_wpisane.rename(columns={"homeGoals": "act_homeGoals", "awayGoals": "act_awayGoals"})

    # Łączymy typy znajomych tylko z rozegranymi meczami
    df_merged = pd.merge(df_typy_for_merge, df_wyniki_for_merge, on="id")
    
    if df_merged.empty:
        st.dataframe(tabela_koncowa.reset_index(), use_container_width=True, hide_index=True)
    else:
        # Konwersja wyników na liczby na wypadek błędów w Supabase
        for col in ["act_homeGoals", "act_awayGoals", "pred_homeGoals", "pred_awayGoals"]:
            df_merged[col] = pd.to_numeric(df_merged[col], errors="coerce").fillna(0).astype(int)

        # Funkcja obliczająca punkty per wiersz
        def kalkulator_punktow(row):
            tg, tk = row["act_homeGoals"], row["act_awayGoals"]
            wg, wk = row["pred_homeGoals"], row["pred_awayGoals"]
            
            if tg == wg and tk == wk:
                return 3  # Dokładny wynik
            elif (tg > tk and wg > wk) or (tg < tk and wg < wk) or (tg == tk and wg == wk):
                return 1  # Trafiony zwycięzca / remis
            return 0

        # Liczymy punkty
        df_merged["Zdobycz"] = df_merged.apply(kalkulator_punktow, axis=1)
        
        # Sumujemy punkty dla każdego gracza
        punkty_graczy = df_merged.groupby("name")["Zdobycz"].sum()
        
        # Aktualizujemy naszą bazową tabelę o zdobyte punkty
        tabela_koncowa["Punkty"] = punkty_graczy
        tabela_koncowa["Punkty"] = tabela_koncowa["Punkty"].fillna(0).astype(int)
        tabela_koncowa = tabela_koncowa.sort_values(by="Punkty", ascending=False).reset_index()
        
        # Dodajemy kolumnę z pozycją (np. 1, 2, 3...)
        tabela_koncowa.index = tabela_koncowa.index + 1
        st.dataframe(tabela_koncowa, use_container_width=True)

# --- SEKCJA 3: PRZEGLĄD TYPÓW ZALOGOWANEGO GRACZA ---
st.header("🔍 Twoje typy")

if df_typy.empty:
    st.info("Brak zapisanych typów w bazie danych.")
else:
    df_user_typy = df_typy[df_typy["name"] == st.session_state.logged_in_user].copy()
    if df_user_typy.empty:
        st.info(f"Jeszcze nie wprowadzono typów.")
    else:
        # Dopełniamy do informacji o meczu z tabeli matches
        df_user_typy = df_user_typy.rename(columns={"homeGoals": "pred_homeGoals", "awayGoals": "pred_awayGoals"})
        df_user_typy = pd.merge(
            df_user_typy,
            df_mecze[["id", "home", "away", "homeGoals", "awayGoals"]],
            on="id",
            how="left",
        )
        
        # Tworzymy ładne opisy
        df_user_typy["Mecz"] = df_user_typy.apply(lambda r: f"{r['home']} vs {r['away']}", axis=1)
        df_user_typy["Twój Typ"] = df_user_typy.apply(lambda r: f"{int(r['pred_homeGoals'])}-{int(r['pred_awayGoals'])}", axis=1)
        
        # Dodajemy wynik rzeczywisty jeśli jest dostępny
        df_user_typy["Wynik"] = df_user_typy.apply(
            lambda r: f"{int(r['homeGoals'])}-{int(r['awayGoals'])}" if not pd.isna(r['homeGoals']) and not pd.isna(r['awayGoals']) and str(r['homeGoals']).strip() != "" and str(r['awayGoals']).strip() != "" else "—",
            axis=1
        )
        
        # Liczymy punkty za każdy mecz jeśli mamy wynik rzeczywisty
        def calc_points_for_match(row):
            if pd.isna(row['homeGoals']) or pd.isna(row['awayGoals']) or str(row['homeGoals']).strip() == "" or str(row['awayGoals']).strip() == "":
                return "—"
            
            tg, tk = int(row['homeGoals']), int(row['awayGoals'])
            wg, wk = int(row['pred_homeGoals']), int(row['pred_awayGoals'])
            
            if tg == wg and tk == wk:
                return "3 ✓"  # Dokładny wynik
            elif (tg > tk and wg > wk) or (tg < tk and wg < wk) or (tg == tk and wg == wk):
                return "1 ✓"  # Trafiony zwycięzca / remis
            return "0 ✗"
        
        df_user_typy["Punkty"] = df_user_typy.apply(calc_points_for_match, axis=1)
        
        # Wybieramy i sortujemy kolumny
        df_display = df_user_typy[["id", "Mecz", "Twój Typ", "Wynik", "Punkty"]].sort_values("id").reset_index(drop=True)
        df_display.index = df_display.index + 1
        
        st.dataframe(
            df_display.rename(columns={"id": "ID"}),
            use_container_width=True,
            hide_index=False
        )