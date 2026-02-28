#Kalkulator som regner ut hvor mye man sitter igjen med når man har et startbeløp og en årlig avkastning som compounder over tid.
#Brukeren legger inn startbeløp og årlig avkastning.
#Programmet vil også regne ut hvis avkastningen blir 3, 5 eller 10 prosent dårligere.
#Programmet skal vise viktigheten av å få de store prosentene.


import matplotlib.pyplot as plt
import matplotlib.ticker as ticker


def beregn_utvikling(startbelop: float, avkastning_prosent: float, antall_ar: int):
    """Returnerer (ar_liste, verdi_liste, sluttverdi) for gitt avkastning."""
    avkastning = avkastning_prosent / 100
    ar = []
    verdi = []
    belop = startbelop

    for i in range(1, antall_ar + 1):
        belop *= (1 + avkastning)
        ar.append(i)
        verdi.append(belop)

    return ar, verdi, belop


def main():
    # Input fra bruker
    startbelop = float(input("Startbeløp (kr): "))
    avkastning_prosent = float(input("Årlig avkastning (%): "))
    antall_ar = int(input("Antall år: "))

    # Lag scenarioer: basis + (basis-3, -5, -10) hvis de ikke blir negative
    scenarioer = [avkastning_prosent]
    for diff in (3, 5, 10):
        ny = avkastning_prosent - diff
        if ny >= 0:
            scenarioer.append(ny)

    # Plot alle scenarioer
    for prosent in scenarioer:
        ar, verdi, slutt = beregn_utvikling(startbelop, prosent, antall_ar)

        # pen prosentvisning i legend
        label_prosent = f"{prosent:.0f}%" if float(prosent).is_integer() else f"{prosent:.1f}%"

        plt.plot(
            ar,
            verdi,
            label=f"Total verdi ({label_prosent})"
        )

        # skriv sluttverdi ved siste punkt (litt offset så tekst ikke kræsjer)
        plt.text(
            ar[-1],
            verdi[-1],
            f"{int(verdi[-1]):,} kr".replace(",", " "),
            ha="left",
            va="bottom"
        )

    # Skriv ut resultater i terminalen (samme rekkefølge som i graf)
    print("\nResultater:")
    for prosent in scenarioer:
        _, _, slutt = beregn_utvikling(startbelop, prosent, antall_ar)
        label_prosent = f"{prosent:.0f}%" if float(prosent).is_integer() else f"{prosent:.1f}%"
        print(f"- {label_prosent}: {slutt:,.0f} kr etter {antall_ar} år".replace(",", " "))

    # Plot-utseende
    plt.title("Utvikling av investering")
    plt.xlabel("År")
    plt.ylabel("Kroner")

    # Formatter y-akse til hele tall med mellomrom
    plt.gca().yaxis.set_major_formatter(
        ticker.FuncFormatter(lambda x, _: f"{int(x):,}".replace(",", " "))
    )

    plt.grid(True)
    plt.legend(loc="upper left")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
