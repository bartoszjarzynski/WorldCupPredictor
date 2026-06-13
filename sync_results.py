"""
Synchronizacja wyników meczów MŚ 2026 z football-data.org do tabeli `matches` w Supabase.

Skrypt:
  1. Pobiera mecze z football-data.org (competition WC).
  2. Bierze tylko mecze ze statusem FINISHED (zakończone, z oficjalnym wynikiem).
  3. Dopasowuje je do wierszy w tabeli `matches` po nazwach drużyn.
  4. Aktualizuje kolumny `homeGoals` i `awayGoals`.

URUCHOMIENIE (lokalnie):
    python3 sync_results.py

Klucze (Supabase service_role + token football-data) czytane są automatycznie z
pliku .streamlit/secrets.toml. Można je też nadpisać zmiennymi środowiskowymi:
    FOOTBALL_DATA_TOKEN, SUPABASE_URL, SUPABASE_SERVICE_KEY

UWAGA: do zapisu używamy klucza service_role (omija RLS). Nigdy go nie commituj.
"""

import os
import sys
import unicodedata

import requests
from supabase import create_client


# --- Konfiguracja: czytamy z ENV, a w razie braku z .streamlit/secrets.toml ---
def _load_config():
    token = os.getenv("FOOTBALL_DATA_TOKEN")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")

    # Fallback dla wygody przy uruchamianiu lokalnym
    if not (token and url and key):
        try:
            import tomllib  # Python 3.11+
            with open(".streamlit/secrets.toml", "rb") as f:
                secrets = tomllib.load(f)
            sb = secrets.get("supabase", {})
            url = url or sb.get("url")
            # Do zapisu potrzebny service_role; anon zwykle nie ma praw UPDATE
            key = key or sb.get("service_role") or sb.get("service_key")
            token = token or secrets.get("football_data", {}).get("token")
        except Exception:
            pass

    missing = [n for n, v in [
        ("FOOTBALL_DATA_TOKEN", token),
        ("SUPABASE_URL", url),
        ("SUPABASE_SERVICE_KEY", key),
    ] if not v]
    if missing:
        sys.exit(f"Brak konfiguracji: {', '.join(missing)}. Ustaw zmienne środowiskowe.")

    return token, url, key


# --- Mapowanie nazw drużyn z API (angielski) na nazwy w Twojej tabeli `matches` ---
# Klucz = nazwa z football-data.org (po angielsku), wartość = nazwa w Twoim DB.
# Dla nazw niepewnych podane są dwa warianty (np. "Turkey" i "Türkiye") -> ten sam kraj.
# Drużyny o identycznej pisowni (Haiti, Australia, Iran, Austria, Ghana, Uzbekistan,
# Panama, Senegal) dopasują się automatycznie i nie muszą tu być.
TEAM_NAME_MAP = {
    "Mexico": "Meksyk",
    "South Korea": "Korea Płd.",
    "Korea Republic": "Korea Płd.",
    "Canada": "Kanada",
    "United States": "USA",
    "USA": "USA",
    "Qatar": "Katar",
    "Brazil": "Brazylia",
    "Haiti": "Haiti",
    "Australia": "Australia",
    "Germany": "Niemcy",
    "Netherlands": "Holandia",
    "Ivory Coast": "WKS",
    "Côte d'Ivoire": "WKS",
    "Sweden": "Szwecja",
    "Spain": "Hiszpania",
    "Belgium": "Belgia",
    "Saudi Arabia": "Arabia",
    "Iran": "Iran",
    "France": "Francja",
    "Iraq": "Irak",
    "Argentina": "Argentyna",
    "Austria": "Austria",
    "Portugal": "Portugalia",
    "England": "Anglia",
    "Ghana": "Ghana",
    "Uzbekistan": "Uzbekistan",
    "Czech Republic": "Czechy",
    "Czechia": "Czechy",
    "Switzerland": "Szwajcaria",
    "Scotland": "Szkocja",
    "Turkey": "Turcja",
    "Türkiye": "Turcja",
    "Ecuador": "Ekwador",
    "Tunisia": "Tunezja",
    "Uruguay": "Urugwaj",
    "New Zealand": "Nowa Zelandia",
    "Norway": "Norwegia",
    "Jordan": "Jordania",
    "Panama": "Panama",
    "Colombia": "Kolumbia",
    "Bosnia and Herzegovina": "Bośnia",
    "Bosnia-Herzegovina": "Bośnia",
    "Morocco": "Maroko",
    "South Africa": "RPA",
    "Curacao": "Curacao",
    "Curaçao": "Curacao",
    "Japan": "Japonia",
    "Paraguay": "Paragwaj",
    "Senegal": "Senegal",
    "Cape Verde": "Republika Zielonego Przylądka",
    "Cabo Verde": "Republika Zielonego Przylądka",
    "Egypt": "Egipt",
    "Croatia": "Chorwacja",
    "DR Congo": "Demokratyczna Republika Konga",
    "Congo DR": "Demokratyczna Republika Konga",
    "Democratic Republic of the Congo": "Demokratyczna Republika Konga",
    "Algeria": "Algieria",
}


def _strip(s):
    """Usuwa ogonki, sprowadza do małych liter i obcina spacje."""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.strip().lower()


# Mapa znormalizowana, żeby dopasowanie do słownika było odporne na pisownię.
_NORM_MAP = {_strip(k): v for k, v in TEAM_NAME_MAP.items()}


def _normalize(name):
    """Normalizacja nazwy do porównań; najpierw tłumaczy z angielskiego wg słownika."""
    if name is None:
        return ""
    base = _strip(name)
    if base in _NORM_MAP:
        return _strip(_NORM_MAP[base])
    return base


def fetch_finished_matches(token):
    url = "https://api.football-data.org/v4/competitions/WC/matches"
    resp = requests.get(url, headers={"X-Auth-Token": token}, timeout=30)
    resp.raise_for_status()
    matches = resp.json().get("matches", [])
    return [m for m in matches if m.get("status") == "FINISHED"]


def main():
    token, url, key = _load_config()
    client = create_client(url, key)

    # 1. Wczytaj wszystkie mecze z Supabase i zbuduj indeks po nazwach drużyn
    rows = client.table("matches").select("id, home, away, homeGoals, awayGoals").execute().data
    index = {(_normalize(r["home"]), _normalize(r["away"])): r for r in rows}

    # 2. Pobierz zakończone mecze z API
    finished = fetch_finished_matches(token)
    print(f"Pobrano {len(finished)} zakończonych meczów z football-data.org.\n")

    updated, skipped, not_found = 0, 0, 0

    for m in finished:
        home = m["homeTeam"]["name"]
        away = m["awayTeam"]["name"]
        hg = m["score"]["fullTime"]["home"]
        ag = m["score"]["fullTime"]["away"]

        if hg is None or ag is None:
            continue

        row = index.get((_normalize(home), _normalize(away)))
        if row is None:
            print(f"  ⚠️  Nie znaleziono w tabeli: {home} vs {away}")
            not_found += 1
            continue

        # Nie nadpisuj, jeśli wynik już taki sam
        if str(row.get("homeGoals")) == str(hg) and str(row.get("awayGoals")) == str(ag):
            skipped += 1
            continue

        client.table("matches").update(
            {"homeGoals": hg, "awayGoals": ag}
        ).eq("id", row["id"]).execute()
        print(f"  ✅  {home} {hg}-{ag} {away}  (id={row['id']})")
        updated += 1

    print(f"\nGotowe. Zaktualizowano: {updated}, bez zmian: {skipped}, niedopasowane: {not_found}")


if __name__ == "__main__":
    main()
