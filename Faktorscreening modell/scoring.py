
# Beregner faktorscorer for alle selskaper i universet.
# Håndterer winsorizing, sektorjustert z-scoring og percentilrangering.
# Inneholder separate funksjoner for verdi, kvalitet, momentum og vekst.

import numpy as np
import pandas as pd
from scipy import stats
from config import WINSORIZE_GRENSE

# Setter opp logging
import logging
logger = logging.getLogger(__name__)


def winsorize(serie: pd.Series) -> pd.Series:
    """
    Kapper ekstremverdier ved 1% og 99% persentil.
    Forhindrer at enkeltselskaper dominerer scoreberegningen.
    """
    nedre = serie.quantile(WINSORIZE_GRENSE)
    øvre = serie.quantile(1 - WINSORIZE_GRENSE)
    return serie.clip(nedre, øvre)


def z_score(serie: pd.Series) -> pd.Series:
    """
    Standardiserer en serie til z-scores.
    Gjennomsnittet blir 0 og standardavviket blir 1.
    """
    if serie.std() == 0:
        return pd.Series(0, index=serie.index)
    return (serie - serie.mean()) / serie.std()


def sektorjustert_z_score(df: pd.DataFrame, kolonne: str, sektor_kolonne: str = "sektor") -> pd.Series:
    """
    Beregner z-score innen hver GICS-sektor.
    Sikrer at vi sammenligner selskaper mot andre i samme bransje.
    """
    resultat = pd.Series(index=df.index, dtype=float)
    for sektor, gruppe in df.groupby(sektor_kolonne):
        if len(gruppe) > 1:
            resultat[gruppe.index] = z_score(gruppe[kolonne])
        else:
            # Hvis bare ett selskap i sektoren, sett z-score til 0
            resultat[gruppe.index] = 0
    return resultat


def percentil_rangering(serie: pd.Series) -> pd.Series:
    """
    Konverterer z-scores til percentilrangering 0-100.
    100 = best i universet, 0 = dårligst.
    """
    return serie.rank(pct=True) * 100


def beregn_verdi_score(df: pd.DataFrame) -> pd.Series:
    """
    Beregner verdi-score basert på P/E, P/B, EV/EBITDA, EV/EBIT og Dividend Yield.
    Lave multipler = bra (inverteres). Høy yield = bra (inverteres ikke).
    """
    score = pd.Series(0.0, index=df.index)
    antall_metrikker = 0

    # Hver metrikk behandles separat – negative verdier ekskluderes per selskap
    metrikker = {
        "pe": True,         # Inverter – lav P/E er bra
        "pb": True,         # Inverter – lav P/B er bra
        "ev_ebitda": True,  # Inverter – lav EV/EBITDA er bra
        "ev_ebit": True,    # Inverter – lav EV/EBIT er bra
        "div_yield": False, # Ikke inverter – høy yield er bra
    }

    for metrikk, inverter in metrikker.items():
        if metrikk not in df.columns:
            continue

        # Ekskluder negative verdier per selskap
        gyldig = df[metrikk].copy()
        gyldig[gyldig < 0] = np.nan

        # Winsorize og z-score
        gyldig = winsorize(gyldig.dropna())
        z = sektorjustert_z_score(df.assign(**{metrikk: gyldig}), metrikk)

        # Inverter retning hvis nødvendig
        if inverter:
            z = -z

        score = score.add(z, fill_value=0)
        antall_metrikker += 1

    return percentil_rangering(score / antall_metrikker) if antall_metrikker > 0 else score


def beregn_kvalitet_score(df: pd.DataFrame) -> pd.Series:
    """
    Beregner kvalitet-score basert på ROIC og ROCE over flere år.
    Høy og stabil avkastning på kapital = bra.
    """
    score = pd.Series(0.0, index=df.index)
    antall_metrikker = 0

    for metrikk in ["roic", "roce"]:
        if metrikk not in df.columns:
            continue

        gyldig = winsorize(df[metrikk].dropna())
        z = sektorjustert_z_score(df.assign(**{metrikk: gyldig}), metrikk)
        score = score.add(z, fill_value=0)
        antall_metrikker += 1

    return percentil_rangering(score / antall_metrikker) if antall_metrikker > 0 else score


def beregn_momentum_score(df: pd.DataFrame) -> pd.Series:
    """
    Beregner momentum-score basert på:
    A) Kursmomemtum 12-1 måneder
    B) Inntjeningsstreak – antall kvartaler på rad med positiv YoY-vekst
    Begge komponenter vektes likt.
    """
    score = pd.Series(0.0, index=df.index)
    antall_komponenter = 0

    # A) Kursmomemtum
    if "kursmomentum" in df.columns:
        gyldig = winsorize(df["kursmomentum"].dropna())
        z = sektorjustert_z_score(df.assign(kursmomentum=gyldig), "kursmomentum")
        score = score.add(z, fill_value=0)
        antall_komponenter += 1

    # B) Inntjeningsstreak
    if "inntjeningsstreak" in df.columns:
        z = sektorjustert_z_score(df, "inntjeningsstreak")
        score = score.add(z, fill_value=0)
        antall_komponenter += 1

    return percentil_rangering(score / antall_komponenter) if antall_komponenter > 0 else score


def beregn_vekst_score(df: pd.DataFrame) -> pd.Series:
    """
    Beregner vekst-score basert på:
    A) YoY-vekst siste kvartal vs samme kvartal året før
    B) Akselerasjon – er veksten bedre enn forrige kvartal?
    Begge komponenter vektes likt.
    """
    score = pd.Series(0.0, index=df.index)
    antall_komponenter = 0

    # A) YoY-vekst – gjennomsnitt av omsetning, EBITDA, EBIT og EPS
    vekst_metrikker = ["vekst_omsetning", "vekst_ebitda", "vekst_ebit", "vekst_eps"]
    vekst_score = pd.Series(0.0, index=df.index)
    antall_vekst = 0

    for metrikk in vekst_metrikker:
        if metrikk not in df.columns:
            continue
        gyldig = winsorize(df[metrikk].dropna())
        z = sektorjustert_z_score(df.assign(**{metrikk: gyldig}), metrikk)
        vekst_score = vekst_score.add(z, fill_value=0)
        antall_vekst += 1

    if antall_vekst > 0:
        score = score.add(vekst_score / antall_vekst, fill_value=0)
        antall_komponenter += 1

    # B) Akselerasjon – binær: er veksten akselererende?
    if "akselerasjon" in df.columns:
        z = sektorjustert_z_score(df, "akselerasjon")
        score = score.add(z, fill_value=0)
        antall_komponenter += 1

    return percentil_rangering(score / antall_komponenter) if antall_komponenter > 0 else score


def beregn_samlet_score(df: pd.DataFrame, aktive_faktorer: dict) -> pd.DataFrame:
    """
    Beregner samlet score som gjennomsnitt av alle aktive faktorers percentilrangering.
    Kun aktive faktorer (True i config) inkluderes, vektet likt.
    """
    faktor_scores = {}

    if aktive_faktorer.get("verdi"):
        faktor_scores["verdi_score"] = beregn_verdi_score(df)

    if aktive_faktorer.get("kvalitet"):
        faktor_scores["kvalitet_score"] = beregn_kvalitet_score(df)

    if aktive_faktorer.get("momentum"):
        faktor_scores["momentum_score"] = beregn_momentum_score(df)

    if aktive_faktorer.get("vekst"):
        faktor_scores["vekst_score"] = beregn_vekst_score(df)

    # Legg til faktorscorer i DataFrame
    for navn, score in faktor_scores.items():
        df[navn] = score

    # Samlet score = gjennomsnitt av aktive faktorers percentilrangering
    score_kolonner = list(faktor_scores.keys())
    if score_kolonner:
        df["samlet_score"] = df[score_kolonner].mean(axis=1)
    else:
        df["samlet_score"] = 0

    return df
