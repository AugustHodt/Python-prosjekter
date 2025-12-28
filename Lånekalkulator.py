import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np


def main():
    # Input fra bruker
    lanebelop = float(input("Lånebeløp (kr): "))
    arlig_rente = float(input("Årlig rente (%): "))
    antall_ar = int(input("Antall år: "))

    rente = arlig_rente / 100 / 12
    terminer = antall_ar * 12

    # Terminbeløp (annuitetslån)
    terminbelop = lanebelop * (rente * (1 + rente) ** terminer) / ((1 + rente) ** terminer - 1)

    restlan = lanebelop
    restlan_hist = []
    rente_hist = []
    avdrag_hist = []

    for _ in range(terminer):
        rente_belop = restlan * rente
        avdrag = terminbelop - rente_belop
        restlan -= avdrag

        restlan_hist.append(restlan)
        rente_hist.append(rente_belop)
        avdrag_hist.append(avdrag)

    print(f"\nTerminbeløp: {terminbelop:,.2f} kr")

    # X-akse i år
    ar = [m / 12 for m in range(1, terminer + 1)]

    #Plot
    fig, ax1 = plt.subplots()

    # Venstre y-akse: Restlån
    ax1.plot(ar, restlan_hist, label="Restlån")
    ax1.set_xlabel("År")
    ax1.set_ylabel("Kroner (restlån)")
    ax1.grid(True)

    # Høyre y-akse: Rente og avdrag per termin
    ax2 = ax1.twinx()
    ax2.plot(ar, rente_hist, label="Rente per termin")
    ax2.plot(ar, avdrag_hist, label="Avdrag per termin")
    ax2.set_ylabel("Kroner per termin")

    # Formatter begge y-akser (tusenskille med mellomrom)
    fmt = ticker.FuncFormatter(lambda x, _: f"{int(x):,}".replace(",", " "))
    ax1.yaxis.set_major_formatter(fmt)
    ax2.yaxis.set_major_formatter(fmt)

    # Kombinert legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right")

    plt.title("Lånekalkulator")
    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
