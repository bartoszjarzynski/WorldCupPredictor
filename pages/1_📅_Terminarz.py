"""Podstrona: Terminarz meczów MŚ 2026 (czas polski)."""

import streamlit as st
import pandas as pd

from core import (
    inject_custom_css, require_login, load_data,
    get_poland_time, parse_match_time, ma_wartosc, format_wynik,
)

st.set_page_config(page_title="Terminarz — Mundial Typer", page_icon="📅", layout="wide")
inject_custom_css()
require_login()

st.title("📅 Terminarz meczów")
st.caption("Wszystkie mecze z bazy, według godziny rozpoczęcia (czas polski).")

df_mecze, _ = load_data()

if df_mecze.empty:
    st.info("Brak meczów w bazie.")
    st.stop()

teraz = get_poland_time()


def _klucz_czasu(r):
    mt = parse_match_time(r.get("start_time"))
    return mt.timestamp() if mt is not None else float("inf")


records = sorted(df_mecze.to_dict("records"), key=_klucz_czasu)

# Odliczanie do najbliższego nierozpoczętego meczu
przyszle = [(parse_match_time(r.get("start_time")), r) for r in records
            if parse_match_time(r.get("start_time")) is not None
            and parse_match_time(r.get("start_time")) > teraz
            and not (ma_wartosc(r.get("homeGoals")) and ma_wartosc(r.get("awayGoals")))]

if przyszle:
    mt_next, nast = przyszle[0]
    delta = mt_next - teraz
    godz = int(delta.total_seconds() // 3600)
    minut = int((delta.total_seconds() % 3600) // 60)
    c1, c2 = st.columns(2)
    c1.metric("Następny mecz", f"{nast['home']} vs {nast['away']}")
    c2.metric("Rozpocznie się za", f"{godz} godz {minut} min")

# Tabela terminarza
wiersze = []
for r in records:
    mt = parse_match_time(r.get("start_time"))
    ma_wynik = ma_wartosc(r.get("homeGoals")) and ma_wartosc(r.get("awayGoals"))
    if ma_wynik:
        status, wynik = "✅ Rozegrany", format_wynik(r.get("homeGoals"), r.get("awayGoals"))
    elif mt is not None and teraz >= mt:
        status, wynik = "🔴 W trakcie", "—"
    else:
        status, wynik = "🕒 Zaplanowany", "—"
    wiersze.append({
        "Mecz": f"{r['home']} vs {r['away']}",
        "Start (PL)": mt.strftime("%d.%m.%Y %H:%M") if mt is not None else "—",
        "Status": status,
        "Wynik": wynik,
    })

df_term = pd.DataFrame(wiersze)
df_term.index = df_term.index + 1


def _styl_status(df):
    style = pd.DataFrame("", index=df.index, columns=df.columns)
    for i in df.index:
        v = df.loc[i, "Status"]
        if "Rozegrany" in v:
            style.loc[i, "Status"] = "color:#22c55e; font-weight:600;"
        elif "trakcie" in v:
            style.loc[i, "Status"] = "color:#f97316; font-weight:700;"
        else:
            style.loc[i, "Status"] = "color:#7df9ff;"
    return style


st.dataframe(df_term.style.apply(_styl_status, axis=None), use_container_width=True)
