
# Innstillinger for faktorscreeningmodellen.
# Her styrer du hvilke faktorer som er aktive, hvilke børser som inkluderes,
# og hvor resultatene lagres. 


import os
from dotenv import load_dotenv

load_dotenv()

# Henter API-nøkkel fra .env-filen i prosjektmappen
API_KEY = os.getenv("BORSDATA_API_KEY", "")

# Aktiver eller deaktiver faktorer ved å sette True/False
# Kun aktive faktorer brukes i scoreberegningen, vektet likt
FAKTORER = {
    "verdi": True,      # P/E, P/B, EV/EBITDA, EV/EBIT, Dividend Yield
    "kvalitet": True,   # ROIC, ROCE over flere år
    "momentum": True,   # Kursmomemtum (12-1m) + inntjeningsstreak
    "vekst": True,      # YoY-vekst + akselerasjon
}

# Hvilke børser som inkluderes i screeningen
MARKEDER = {
    "oslo": True,
    "stockholm": True,
    "kobenhavn": True,
}

# Begrens antall selskaper som behandles – nyttig for rask testing
# Sett til None for å kjøre hele universet
TEST_ANTALL = None

# Filtrer kun aksjer som er kvalifisert for Aksjesparekonto (ASK)
# Ekskluderer First North, Euronext Growth, Spotlight og NGM
KUN_ASK = True

# Ekskluder hele sektorer fra screeningen
EKSKLUDER_SEKTORER = [
    "Health Care",   # Ekskluderer legemiddel, biotek, medtech osv.
]

# Ekskluder spesifikke bransjer (Børsdata branchId)
# 3 = Olja & Gas - Transport (shippingselskaper i Energy-sektoren)
# 41 = Sjöfart & Rederi (øvrig shipping i Industrials)
EKSKLUDER_BRANSJER = [3, 41]

# Grense for winsorizing – kapper ekstremverdier ved 1% og 99% persentil
# Forhindrer at enkeltselskaper dominerer scoreberegningen
WINSORIZE_GRENSE = 0.01

# Mappe og filnavn for Excel-output
OUTPUT_MAPPE = "output"
OUTPUT_FILNAVN = "faktorscreening_resultat.xlsx"