import os
import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
import json

# Konfiguracja strony
st.set_page_config(page_title="Mundial Typer 2026", page_icon="⚽", layout="centered")

# --- KONFIGURACJA EKIPY ---
# Wpisz tutaj dokładnie 8 nicków Twoich znajomych
LISTA_TYPEROW = ["Kamil Kiwer", "Jakub Szabat", "Bartosz Jarzyński", "Mateusz Panic", "Jakub Michalczyk", "Bartek Michalczyk", "Fabian Gołębiowski", "Piotr Strusz"]

st.title("🏆 Oficjalny Typer Mundialu")
st.write("Wprowadzaj swoje typy i śledź tabelę na żywo!")

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


@st.cache_data(ttl=10)
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
    mecze_do_typowania = df_mecze[home_empty | away_empty].sort_values("id")

    if mecze_do_typowania.empty:
        st.info("Wszystkie mecze z zakładki 'Mecze' zostały już rozegrane i uzupełnione!")
    else:
        # Tworzymy ładny opis dla selectboxa, np. "Mecz 1: USA vs Maroko"
        mecze_do_typowania["Opis"] = mecze_do_typowania.apply(
            lambda r: f"Mecz {r['id']}: {r['home']} vs {r['away']}", axis=1
        )
        
        with st.form("formularz_typu", clear_on_submit=False):
            wybrany_nick = st.selectbox("Wybierz swój Nick:", [""] + LISTA_TYPEROW)
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
                if not wybrany_nick:
                    st.error("Musisz wybrać swój Nick z listy!")
                else:
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