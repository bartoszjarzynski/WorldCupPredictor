"""Podstrona: Kto obstawił — macierz meczów i graczy.

Dla każdego jeszcze nierozegranego meczu pokazuje wszystkich graczy i kolorem
oznacza, czy dany gracz już obstawił (zielony) czy jeszcze nie (czerwony).
Mecze, które zostały już rozegrane (mają oficjalny wynik), są pomijane.
"""

import streamlit as st
import pandas as pd

from core import (
    inject_custom_css, require_login, load_data, LISTA_TYPEROW,
    get_poland_time, parse_match_time, ma_wartosc,
)

st.set_page_config(page_title="Obstawienia — Mundial Typer", page_icon="✅", layout="wide")
inject_custom_css()
require_login()

st.title("✅ Kto obstawił")
st.caption("Zielony = gracz już obstawił dany mecz, czerwony = jeszcze nie. "
           "Rozegrane mecze (z wynikiem) są pominięte.")

df_mecze, df_typy = load_data()

if df_mecze.empty:
    st.info("Brak meczów w bazie.")
    st.stop()

uzytkownik = st.session_state.get("logged_in_user")


def _klucz_czasu(r):
    mt = parse_match_time(r.get("start_time"))
    return mt.timestamp() if mt is not None else float("inf")


# Tylko mecze nierozegrane (bez oficjalnego wyniku), chronologicznie
nierozegrane = [
    r for r in df_mecze.to_dict("records")
    if not (ma_wartosc(r.get("homeGoals")) and ma_wartosc(r.get("awayGoals")))
]
nierozegrane.sort(key=_klucz_czasu)

if not nierozegrane:
    st.success("🎉 Wszystkie mecze zostały już rozegrane — nie ma nic do obstawienia.")
    st.stop()

ZIELONY = "background-color: rgba(34,197,94,0.45); color:#eafff1; font-weight:700; text-align:center;"
CZERWONY = "background-color: rgba(239,68,68,0.42); color:#ffecec; font-weight:700; text-align:center;"
LICZNIK_OK = "color:#22c55e; font-weight:700;"
LICZNIK_BRAK = "color:#f97316; font-weight:700;"

ile_graczy = len(LISTA_TYPEROW)
teraz = get_poland_time()

wiersze = []
style_wiersze = []
for r in nierozegrane:
    mid = int(r["id"])
    mt = parse_match_time(r.get("start_time"))
    obstawili = set(df_typy[df_typy["id"] == mid]["name"]) if not df_typy.empty else set()
    licz = sum(1 for g in LISTA_TYPEROW if g in obstawili)

    if mt is not None and teraz >= mt:
        start_txt = (mt.strftime("%d.%m %H:%M") if mt is not None else "—") + " 🔴"
    else:
        start_txt = mt.strftime("%d.%m %H:%M") if mt is not None else "—"

    row = {
        "Mecz": f"{r['home']} vs {r['away']}",
        "Start (PL)": start_txt,
        "Obstawili": f"{licz}/{ile_graczy}",
    }
    srow = {
        "Mecz": "",
        "Start (PL)": "",
        "Obstawili": LICZNIK_OK if licz == ile_graczy else LICZNIK_BRAK,
    }
    for g in LISTA_TYPEROW:
        kol = f"{g} (Ty)" if g == uzytkownik else g
        if g in obstawili:
            row[kol] = "✓"
            srow[kol] = ZIELONY
        else:
            row[kol] = "✗"
            srow[kol] = CZERWONY
    wiersze.append(row)
    style_wiersze.append(srow)

df_obs = pd.DataFrame(wiersze)
df_style = pd.DataFrame(style_wiersze)
df_obs.index = df_obs.index + 1
df_style.index = df_obs.index

st.dataframe(
    df_obs.style.apply(lambda _: df_style, axis=None),
    use_container_width=True,
)

st.markdown(
    "<small>"
    "<span style='background:rgba(34,197,94,0.45);padding:2px 8px;border-radius:6px;'>🟢 ✓ obstawił</span>&nbsp;&nbsp;"
    "<span style='background:rgba(239,68,68,0.42);padding:2px 8px;border-radius:6px;'>🔴 ✗ jeszcze nie obstawił</span>"
    "&nbsp;&nbsp;·&nbsp;&nbsp;🔴 przy dacie = mecz już się rozpoczął"
    "</small>",
    unsafe_allow_html=True,
)

# Skrót dla najbliższego nadchodzącego meczu (jeszcze przed startem)
przyszle = [r for r in nierozegrane
            if (mt := parse_match_time(r.get("start_time"))) is not None and mt > teraz]
if przyszle:
    nast = przyszle[0]
    mid = int(nast["id"])
    obstawili = set(df_typy[df_typy["id"] == mid]["name"]) if not df_typy.empty else set()
    brakujacy = [g for g in LISTA_TYPEROW if g not in obstawili]
    st.subheader(f"➡️ Najbliższy mecz: {nast['home']} vs {nast['away']}")
    if not brakujacy:
        st.success("✅ Wszyscy już obstawili ten mecz!")
    else:
        st.warning(f"⚠️ Jeszcze nie obstawili ({len(brakujacy)}/{ile_graczy}): "
                   + ", ".join(brakujacy))
