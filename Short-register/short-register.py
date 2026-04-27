"""
short_register.py
Henter daglig shortregister fra Finanstilsynet i Norge og Sverige og sender det på e-post kl. 15:30.

E-posten inneholder:
  1. Alle selskaper i registeret (med endringer fra i går)
  2. Dine spesifikke Norske selskaper
  3. Topp 10 mest shortede aksjer
  4. Dine spesifikke Svenske selskaper
"""

import requests
import pandas as pd
import os
import json
from pathlib import Path
from datetime import date


# ─────────────────────────────────────────────
#  INNSTILLINGER  ← Legg til selskaper du vil følge her
# ─────────────────────────────────────────────

MINE_SELSKAPER = [
    "Hexagon Composites",
    "Nordic Semiconductor",
    "Vend Marketplaces",
    "Kid",
    "Cadeler",
    "Europris",
]

MINE_SVENSKE_SELSKAPER = [
    "Byggmax Group AB",
    "Essity Aktiebolag (publ)",
    "Elekta AB (publ)",
    "JM AB",
    "Clas Ohlson Aktiebolag",
    "RVRC Holding AB",
    "Nelly Group AB (publ)",
    "Evolution AB (publ)",
    "VBG Group",
    "Husqvarna AB",
    "Securitas AB",
    "Hemnet Group AB (publ)",
]

CACHE_FIL = "forrige_short.json"  # Lagrer gårsdagens data for sammenligning


# ─────────────────────────────────────────────
#  HENT DATA
# ─────────────────────────────────────────────

def hent_shortregister() -> pd.DataFrame:
    print("📡 Henter shortregister fra Finanstilsynet...")
    url = "https://ssr.finanstilsynet.no/api/v2/instruments"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    rader = []
    for instrument in data:
        navn = instrument["issuerName"]
        if instrument["events"]:
            siste_event = max(instrument["events"], key=lambda e: e["date"])
            if siste_event["shortPercent"] == 0:
                continue
            rader.append({
                "selskap": navn,
                "short_pst": siste_event["shortPercent"],
                "dato": siste_event["date"][8:10] + "." + siste_event["date"][5:7] + "." + siste_event["date"][:4],
                "dato_sort": siste_event["date"][:10],
            })

    df = pd.DataFrame(rader).sort_values("dato_sort", ascending=False).drop(columns=["dato_sort"])
    print(f"  ✅ Hentet {len(df)} shortposisjoner")
    return df

def hent_svensk_shortregister() -> pd.DataFrame:
    print("📡 Henter svensk shortregister fra Finansinspektionen...")
    import io
    url = "https://www.fi.se/sv/vara-register/blankningsregistret/"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, timeout=120)
    df = pd.read_html(io.StringIO(resp.text), decimal=",", thousands=".")[0]
    df = df.rename(columns={
        "Emittentens namn": "selskap",
        "Positionsdatum senaste position": "dato",
        "Summa blankning %": "short_pst",
    })
    df["dato"] = pd.to_datetime(df["dato"]).dt.strftime("%d.%m.%Y")
    df = df[["selskap", "short_pst", "dato"]].dropna()
    df = df[df["short_pst"] > 0]
    print(f"  ✅ Hentet {len(df)} svenske shortposisjoner")
    return df


def last_forrige_data() -> dict:
    """Laster gårsdagens shortdata fra cache."""
    if Path(CACHE_FIL).exists():
        with open(CACHE_FIL, "r") as f:
            return json.load(f)
    return {}


def lagre_dagens_data(df: pd.DataFrame):
    """Lagrer dagens data for sammenligning i morgen."""
    data = df.groupby("selskap")["short_pst"].max().to_dict()
    with open(CACHE_FIL, "w") as f:
        json.dump(data, f)


def endring_pil(tidligere, naavaerende: float) -> str:
    """Viser pil og endring fra i går."""
    if tidligere is None:
        return "<span style='color: gray;'>NY</span>"
    diff = naavaerende - tidligere
    if diff > 0.1:
        return f"<span style='color: red;'>↑ +{diff:.2f}%</span>"
    elif diff < -0.1:
        return f"<span style='color: green;'>↓ {diff:.2f}%</span>"
    else:
        return "<span style='color: gray;'>→</span>"


# ─────────────────────────────────────────────
#  LAG HTML-INNHOLD
# ─────────────────────────────────────────────

def lag_epost_html(df: pd.DataFrame, forrige: dict) -> str:
    """Setter sammen hele HTML-e-posten."""
    dato = date.today().strftime("%d.%m.%Y")
    df_svensk = hent_svensk_shortregister()

    # Topp 10 mest shortede
    topp10 = df.drop_duplicates(subset=["selskap"]).sort_values("short_pst", ascending=False).head(10)
    topp10_html = lag_tabell_html(topp10, forrige, "🔝 Topp 10 mest shortede", "#c0392b")

    # Mine selskaper
    mine_rader = []
    for navn in MINE_SELSKAPER:
        treff = df[df["selskap"].str.contains(navn, case=False, na=False)]
        if not treff.empty:
            rad = treff.iloc[0]
            mine_rader.append({"selskap": rad["selskap"], "short_pst": rad["short_pst"], "dato": rad["dato"]})
        else:
            mine_rader.append({"selskap": navn, "short_pst": 0.0, "dato": "–"})
    mine = pd.DataFrame(mine_rader)
    mine_html = lag_tabell_html(mine, forrige, "⭐ Dine selskaper", "#2980b9")

    # Mine svenske selskaper
    mine_svenske_rader = []
    for navn in MINE_SVENSKE_SELSKAPER:
        treff = df_svensk[df_svensk["selskap"].str.contains(navn, case=False, na=False, regex=False)]
        if not treff.empty:
            rad = treff.iloc[0]
            mine_svenske_rader.append({"selskap": rad["selskap"], "short_pst": rad["short_pst"], "dato": rad["dato"]})
        else:
            mine_svenske_rader.append({"selskap": navn, "short_pst": 0.0, "dato": "–"})
    mine_svenske = pd.DataFrame(mine_svenske_rader)
    mine_svenske_html = lag_tabell_html(mine_svenske, {}, "🇸🇪 Mine svenske selskaper", "#27ae60")

    # Alle selskaper
    alle_html = lag_tabell_html(df, forrige, "📋 Alle shortposisjoner", "#2c3e50")

    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 900px; margin: auto; padding: 20px;">
        <h2 style="color: #2c3e50; border-bottom: 2px solid #2c3e50; padding-bottom: 10px;">
            📉 Shortregister Norge – {dato}
        </h2>
        <p style="color: #555;">
            Daglig oppdatering fra Finanstilsynet. Viser alle shortposisjoner over 0,5% av utestående aksjer.
            Totalt <b>{len(df)}</b> posisjoner rapportert.
        </p>

        {alle_html}
        {topp10_html}
        {mine_html}
        {mine_svenske_html}

        <p style="color: #aaa; font-size: 11px; margin-top: 30px;">
            Kilde: Finanstilsynet.no | Oppdatert automatisk kl. 15:30 hver ukedag
        </p>
    </body>
    </html>"""


def lag_tabell_html(df: pd.DataFrame, forrige: dict, tittel: str, farge: str) -> str:
    rader = ""
    for i, (_, rad) in enumerate(df.iterrows()):
        selskap   = str(rad.get("selskap", "–"))
        short_pst = rad.get("short_pst", 0)
        dato      = str(rad.get("dato", "–"))
        tidligere = forrige.get(selskap)
        pil       = endring_pil(tidligere, short_pst)
        rad_farge = "#f9f9f9" if i % 2 == 0 else "white"

        rader += f"""
        <tr style="background: {rad_farge};">
            <td style="padding: 8px;">{i+1}</td>
            <td style="padding: 8px;"><b>{selskap}</b></td>
            <td style="padding: 8px;"><b>{short_pst:.2f}%</b></td>
            <td style="padding: 8px;">{pil}</td>
            <td style="padding: 8px; color: gray; font-size: 11px;">{dato}</td>
        </tr>"""

    kolonner = f"""
        <th style="padding: 8px; background: {farge}; color: white; text-align: left;">#</th>
        <th style="padding: 8px; background: {farge}; color: white; text-align: left;">Selskap</th>
        <th style="padding: 8px; background: {farge}; color: white; text-align: left;">Short %</th>
        <th style="padding: 8px; background: {farge}; color: white; text-align: left;">Endring</th>
        <th style="padding: 8px; background: {farge}; color: white; text-align: left;">Dato</th>"""

    return f"""
    <h3 style="color: {farge}; margin-top: 30px;">{tittel}</h3>
    <table style="border-collapse: collapse; width: 100%; font-size: 13px;">
        <thead><tr>{kolonner}</tr></thead>
        <tbody>{rader}</tbody>
    </table>"""


# ─────────────────────────────────────────────
#  SEND E-POST
# ─────────────────────────────────────────────

def send_epost(html: str, antall: int):
    """Sender e-post via Resend."""
    import resend

    dato = date.today().strftime("%d.%m.%Y")
    resend.api_key = os.environ["RESEND_API_KEY"]

    resend.Emails.send({
        "from": "onboarding@resend.dev",
        "to": os.environ["EMAIL"],
        "subject": f"📉 Shortregister Norge – {dato} ({antall} posisjoner)",
        "html": html,
    })
    print(f"  ✅ E-post sendt!")


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    df      = hent_shortregister()
    forrige = last_forrige_data()
    html    = lag_epost_html(df, forrige)
    send_epost(html, len(df))
    lagre_dagens_data(df)
