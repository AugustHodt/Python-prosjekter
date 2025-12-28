#Programmet er deisgnet slik at man ønsker å vite hvor lang tid det tar
#å spare seg til et visst beløp gitt månedtlige beløp og årlig avkastning


import matplotlib.pyplot as plt


def tid_til_malbelop(malbelop: float, manedlig_innskudd: float, rente_prosent: float):
    total = 0.0
    renteinntekter = 0.0
    maneder = 0

    historikk_total = []
    historikk_rente = []
    historikk_innskudd = []

    while total < malbelop:
        total += manedlig_innskudd
        historikk_innskudd.append(total - renteinntekter)

        rente_for_maneden = total * (rente_prosent / 100.0) / 12.0
        renteinntekter += rente_for_maneden
        total += rente_for_maneden

        historikk_total.append(total)
        historikk_rente.append(renteinntekter)
        maneder += 1

        # enkel sikkerhetsbrems
        if maneder > 2000:
            break

    return maneder, total, renteinntekter, historikk_total, historikk_innskudd, historikk_rente


def main():
    malbelop = float(input("Målbeløp (kr): "))
    manedlig_innskudd = float(input("Månedlig innskudd (kr): "))
    rente = float(input("Årlig rente i % (f.eks 4): "))

    maneder, total, renteinntekter, total_hist, innskudd_hist, rente_hist = tid_til_malbelop(
        malbelop, manedlig_innskudd, rente
    )

    ar = maneder // 12
    rest = maneder % 12
    print(f"Du når målet på ca. {ar} år og {rest} måneder.")
    print(f"Total: {total:,.2f} kr (rente: {renteinntekter:,.2f} kr)")


    x = [m / 12 for m in range(1, len(total_hist) + 1)]

    plt.plot(x, total_hist, label="Total")
    plt.plot(x, innskudd_hist, label="Innskudd")
    plt.plot(x, rente_hist, label="Rente")

    plt.title("Sparekalkulator")
    plt.xlabel("År")
    plt.ylabel("Kroner")

    import math
    max_year = math.ceil(x[-1])
    plt.xticks(range(0, max_year + 1))

    plt.grid(True)
    plt.legend()

    import numpy as np
    max_year = int(max(x))
    if max_year > 30:
        plt.xticks(np.arange(0, max_year + 1, 5))

    import matplotlib.ticker as ticker

    plt.gca().yaxis.set_major_formatter(
        ticker.FuncFormatter(lambda x, _: f"{int(x):,}".replace(",", " "))
    )

    x_slutt = x[-1]
    total_slutt = total_hist[-1]
    innskudd_slutt = innskudd_hist[-1]
    rente_slutt = rente_hist[-1]

    plt.text(x_slutt, total_slutt,
             f"{int(total_slutt):,} kr",
             color="blue", fontsize=10, ha="right")

    plt.text(x_slutt, innskudd_slutt,
             f"{int(innskudd_slutt):,} kr",
             color="orange", fontsize=10, ha="right")

    plt.text(x_slutt, rente_slutt,
             f"{int(rente_slutt):,} kr",
             color="green", fontsize=10, ha="right")

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
