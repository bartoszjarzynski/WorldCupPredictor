"""Podstrona: Statystyki graczy i wykresy."""

import streamlit as st
import pandas as pd

from core import (
    inject_custom_css, require_login, load_data, LISTA_TYPEROW,
    parse_match_time, ma_wartosc, oblicz_punkty,
)

st.set_page_config(page_title="Statystyki — Mundial Typer", page_icon="📈", layout="wide")
inject_custom_css()
require_login()

st.title("📈 Statystyki & Wykresy")

df_mecze, df_typy = load_data()

if df_mecze.empty:
    st.info("Brak meczów w bazie.")
    st.stop()


def _klucz_czasu(r):
    mt = parse_match_time(r.get("start_time"))
    return mt.timestamp() if mt is not None else float("inf")


# Rozegrane mecze (z wynikiem), chronologicznie
rozegrane = [r for r in df_mecze.to_dict("records")
             if ma_wartosc(r.get("homeGoals")) and ma_wartosc(r.get("awayGoals"))]
rozegrane.sort(key=_klucz_czasu)

if not rozegrane:
    st.info("Statystyki pojawią się po pierwszych rozegranych meczach.")
    st.stop()
if df_typy.empty:
    st.info("Brak zapisanych typów.")
    st.stop()

# Akumulacja statystyk i punktów w czasie
stat = {g: {"typy": 0, "dokladne": 0, "trafione": 0, "pudla": 0, "punkty": 0} for g in LISTA_TYPEROW}
kumulacja = {g: [] for g in LISTA_TYPEROW}
biezace = {g: 0 for g in LISTA_TYPEROW}
etykiety = []

for idx, r in enumerate(rozegrane, start=1):
    mid = int(r["id"])
    tg, tk = int(float(r["homeGoals"])), int(float(r["awayGoals"]))
    preds = {p["name"]: p for _, p in df_typy[df_typy["id"] == mid].iterrows()}
    for g in LISTA_TYPEROW:
        if g in preds:
            try:
                wg, wk = int(float(preds[g]["homeGoals"])), int(float(preds[g]["awayGoals"]))
                pkt = oblicz_punkty(tg, tk, wg, wk)
                stat[g]["typy"] += 1
                stat[g]["punkty"] += pkt
                if pkt == 3:
                    stat[g]["dokladne"] += 1
                elif pkt == 1:
                    stat[g]["trafione"] += 1
                else:
                    stat[g]["pudla"] += 1
                biezace[g] += pkt
            except Exception:
                pass
        kumulacja[g].append(biezace[g])
    etykiety.append(f"{idx}. {str(r['home'])[:3]}–{str(r['away'])[:3]}")

# --- Tabela statystyk ---
wiersze = []
for g in LISTA_TYPEROW:
    s = stat[g]
    skutecznosc = round(100 * (s["dokladne"] + s["trafione"]) / s["typy"], 1) if s["typy"] else 0.0
    wiersze.append({
        "Gracz": g,
        "Punkty": s["punkty"],
        "Typy": s["typy"],
        "🟢 Dokładne": s["dokladne"],
        "🟠 Trafione": s["trafione"],
        "🔴 Pudła": s["pudla"],
        "Skuteczność %": skutecznosc,
    })
df_stat = pd.DataFrame(wiersze).sort_values("Punkty", ascending=False).reset_index(drop=True)
df_stat.index = df_stat.index + 1

st.subheader("🏅 Statystyki graczy")
st.dataframe(df_stat, use_container_width=True)

st.subheader("📊 Punkty według graczy")
st.bar_chart(df_stat.set_index("Gracz")["Punkty"])

st.subheader("📈 Skumulowane punkty w czasie")
df_kum = pd.DataFrame(kumulacja, index=etykiety)
st.line_chart(df_kum)
st.caption("Oś X: kolejne rozegrane mecze (chronologicznie). Każda linia to jeden gracz.")
