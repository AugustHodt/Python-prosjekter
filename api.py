
# Håndterer all kommunikasjon med Børsdata sitt REST API.
# Henter selskaper, kurser, kvartalsrapporter og nøkkeltall.
# Respekterer Børsdata sin rate limit på 100 kall per 10 sekunder.


import requests
import time
import logging
import pandas as pd
from config import API_KEY

# Setter opp logging slik at vi får tydelige meldinger i terminalen
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Basis-URL for Børsdata API
BASE_URL = "https://apiservice.borsdata.se/v1"

# Børsdata tillater maks 100 kall per 10 sekunder
# Vi venter 0.1 sekunder mellom hvert kall for å være trygge
RATE_LIMIT_DELAY = 0.1


def api_kall(endepunkt: str, params: dict = {}) -> dict:
    """
    Generisk funksjon for API-kall til Børsdata.
    Håndterer feil og rate limiting automatisk.
    """
    params["authKey"] = API_KEY
    url = f"{BASE_URL}/{endepunkt}"

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        time.sleep(RATE_LIMIT_DELAY)
        return response.json()
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP-feil ved kall til {endepunkt}: {e}")
        return {}
    except requests.exceptions.ConnectionError:
        logger.error(f"Tilkoblingsfeil – sjekk internettforbindelsen")
        return {}
    except Exception as e:
        logger.error(f"Uventet feil: {e}")
        return {}


def hent_instrumenter() -> pd.DataFrame:
    """
    Henter selskaper basert på MARKEDER-innstillingen i config.py.
    Returnerer en DataFrame med selskapsnavn, ticker, sektor og land.
    Børsdata countryId: Sverige=1, Norge=2, Finland=3, Danmark=4
    """
    from config import MARKEDER, EKSKLUDER_SEKTORER, EKSKLUDER_BRANSJER, KUN_ASK

    logger.info("Henter liste over alle selskaper...")
    data = api_kall("instruments")

    if not data:
        logger.error("Kunne ikke hente selskaper")
        return pd.DataFrame()

    df = pd.DataFrame(data.get("instruments", []))

    # Filtrer ut kun aksjer (instrument=0), ikke indekser
    df = df[df["instrument"] == 0]

    # Børsdata countryId: Sverige=1, Norge=2, Danmark=4
    land_ids = []
    if MARKEDER.get("oslo"):      land_ids.append(2)
    if MARKEDER.get("stockholm"): land_ids.append(1)
    if MARKEDER.get("kobenhavn"): land_ids.append(4)

    df = df[df["countryId"].isin(land_ids)]

    # Hent sektor- og landnavn for visning
    sektor_data = api_kall("sectors")

    # Oversetter svenske GICS-sektornavn til engelsk
    svensk_til_engelsk = {
        "Energi":                  "Energy",
        "Material":                "Materials",
        "Industri":                "Industrials",
        "Sällanköpsvaror":         "Consumer Discretionary",
        "Dagligvaror":             "Consumer Staples",
        "Hälsovård":               "Health Care",
        "Finans & Fastighet":      "Financials",
        "Fastigheter":             "Real Estate",
        "Informationsteknik":      "Information Technology",
        "Kommunikationstjänster":  "Communication Services",
        "Kraftförsörjning":        "Utilities",
    }

    sektor_map = {
        s["id"]: svensk_til_engelsk.get(s["name"], s["name"])
        for s in sektor_data.get("sectors", [])
    }

    land_map = {1: "Sverige", 2: "Norge", 4: "Danmark"}

    df["sektor"] = df["sectorId"].map(sektor_map)
    df["land"] = df["countryId"].map(land_map)

    # Filtrer kun ASK-kvalifiserte markeder
    if KUN_ASK:
        ask_market_ids = {9, 10, 11, 12, 1, 2, 3, 20, 21, 22}
        df = df[df["marketId"].isin(ask_market_ids)]

    # Ekskluder hele sektorer
    if EKSKLUDER_SEKTORER:
        df = df[~df["sektor"].isin(EKSKLUDER_SEKTORER)]

    # Ekskluder spesifikke bransjer
    if EKSKLUDER_BRANSJER:
        df = df[~df["branchId"].isin(EKSKLUDER_BRANSJER)]

    aktive = [k for k, v in MARKEDER.items() if v]
    logger.info(f"Hentet {len(df)} selskaper fra {', '.join(aktive)}")
    return df


def hent_nøkkeltall(instrument_id: int) -> dict:
    """
    Henter nøkkeltall for ett selskap via individuelle KPI-endepunkt.
    Verdiметrikker: siste r12-verdi (dagens prising).
    Kvalitetsmetrikker: 10-års snitt på årsdata (strukturell lønnsomhet).
    Børsdata KPI-IDer: P/E=2, P/B=4, EV/EBIT=10, EV/EBITDA=11, ROIC=37, ROCE=36, Div.Yield=1
    """
    # Verdiметrikker – siste trailing 12-måneder verdi
    verdi_kpis = {
        "pe":        2,
        "pb":        4,
        "ev_ebit":   10,
        "ev_ebitda": 11,
        "div_yield": 1,
    }

    # Kvalitetsmetrikker – 10-års snitt for å fange strukturell lønnsomhet
    kvalitet_kpis = {
        "roic": 37,
        "roce": 36,
    }

    resultat = {}

    for navn, kpi_id in verdi_kpis.items():
        data = api_kall(f"instruments/{instrument_id}/kpis/{kpi_id}/r12/mean/history", {"maxCount": 1})
        verdier = data.get("values", [])
        if verdier:
            resultat[navn] = verdier[0].get("v")

    for navn, kpi_id in kvalitet_kpis.items():
        data = api_kall(f"instruments/{instrument_id}/kpis/{kpi_id}/year/mean/history", {"maxCount": 10})
        verdier = data.get("values", [])
        if verdier:
            gyldige = [v.get("v") for v in verdier if v.get("v") is not None and v.get("v") > 0]
            if gyldige:
                resultat[navn] = sum(gyldige) / len(gyldige)

    # Market cap i millioner lokal valuta (KPI 49) – brukes til størrelsesfiltrering
    data = api_kall(f"instruments/{instrument_id}/kpis/49/r12/mean/history", {"maxCount": 1})
    verdier = data.get("values", [])
    if verdier:
        resultat["market_cap_mill"] = verdier[0].get("v")

    return resultat


def hent_kvartalstall(instrument_id: int) -> pd.DataFrame:
    """
    Henter kvartalsrapporter for ett selskap.
    Brukes til vekst- og momentumberegning.
    """
    data = api_kall(f"instruments/{instrument_id}/reports/quarter")

    if not data:
        return pd.DataFrame()

    rapporter = data.get("reports", [])
    return pd.DataFrame(rapporter)


def hent_kurser(instrument_id: int) -> pd.DataFrame:
    """
    Henter historiske kurser for ett selskap.
    Brukes til å beregne kursmomemtum (12-1m).
    """
    data = api_kall(f"instruments/{instrument_id}/stockprices")

    if not data:
        return pd.DataFrame()

    kurser = data.get("stockPricesList", [])
    return pd.DataFrame(kurser)