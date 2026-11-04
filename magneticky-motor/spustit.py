"""Spustí celý výpočet, vytiskne souhrn a uloží grafy do ./vystupy/.

    python3 spustit.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import magnetostatika as ms  # noqa: E402
import motor_model as mm  # noqa: E402

VYSTUPY = Path(__file__).parent / "vystupy"
DEG = np.degrees(mm.UHLY)


def graf_pole(magnet: mm.Magnet) -> list[str]:
    z = np.linspace(0.0002, 0.02, 60)
    analyt = [ms.pole_na_ose_analyticky(magnet.sirka, magnet.vyska, magnet.tloustka,
                                        magnet.br, d) for d in z]
    mag = ms.magnet_kvadr(magnet.sirka, magnet.vyska, magnet.tloustka, magnet.br, 0, 0)
    model = ms.pole_B(mag, np.column_stack([magnet.tloustka / 2 + z, 0 * z, 0 * z]))[:, 0]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(z * 1e3, np.array(analyt) * 1e3, lw=3, alpha=0.4, label="analytický vzorec")
    ax.plot(z * 1e3, model * 1e3, "k--", label="model (ekviv. proudy)")
    ax.set(xlabel="vzdálenost od plochy magnetu [mm]", ylabel="B na ose [mT]",
           title="Pole magnetu 20×10×2 mm (N50)")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(VYSTUPY / "1_pole_magnetu.png", dpi=120)
    plt.close(fig)
    return [f"B na ploše magnetu: {analyt[0] * 1e3:.0f} mT, v 2 mm: "
            f"{np.interp(0.002, z, analyt) * 1e3:.0f} mT, v 5 mm: "
            f"{np.interp(0.005, z, analyt) * 1e3:.0f} mT"]


def scenare_bez_napajeni(magnet: mm.Magnet, rotor: mm.Rotor) -> list[str]:
    """Rotor + pevné magnety. Hledáme čistou práci za otáčku."""
    scenare = {
        "A) 1 odpudivý statorový magnet, mezera 2 mm":
            mm.stator_magnety(magnet, rotor, [0.0], [0.002]),
        "B) 'V-gate' spirála: 7 magnetů, mezera 12 -> 2 mm":
            mm.stator_magnety(magnet, rotor, np.radians(np.linspace(0, 90, 7)),
                              np.linspace(0.012, 0.002, 7)),
        "C) spirála přitažlivých magnetů 12 -> 2 mm":
            mm.stator_magnety(magnet, rotor, np.radians(np.linspace(0, 90, 7)),
                              np.linspace(0.012, 0.002, 7), odpudivy=False),
    }
    radky = []
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 7), sharex=True)
    for nazev, zdroj in scenare.items():
        t = mm.superpozice(mm.moment_na_magnet_rotoru(magnet, rotor, zdroj), rotor)
        prace = mm.prace_za_otacku(t)
        kumul = np.cumsum(t) * (mm.UHLY[1] - mm.UHLY[0])
        ax1.plot(DEG, t * 1e3, label=nazev)
        ax2.plot(DEG, kumul * 1e3, label=nazev)
        radky.append(f"{nazev}: max moment {np.max(np.abs(t)) * 1e3:.2f} mN·m, "
                     f"max uložená energie {np.ptp(kumul) * 1e3:.3f} mJ, "
                     f"PRÁCE ZA OTÁČKU {prace:+.1e} J "
                     f"(= {abs(prace) / np.ptp(kumul):.0e} × max. uložené energie)")
    ax1.set(ylabel="moment na rotor [mN·m]", title="Rotor jen s permanentními magnety")
    ax2.set(xlabel="natočení rotoru [°]", ylabel="kumulovaná práce [mJ]")
    for ax in (ax1, ax2):
        ax.grid(alpha=0.3)
        ax.axhline(0, color="k", lw=0.8)
    ax1.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(VYSTUPY / "2_magnety_bez_napajeni.png", dpi=120)
    plt.close(fig)
    return radky


def graf_motoru(k_t, okno, provoz, civka, napajeni, rotor, treni) -> None:
    fig, axs = plt.subplots(3, 1, figsize=(8, 10))
    axs[0].plot(DEG, k_t * 1e3)
    axs[0].axvspan(okno.zapnuti, okno.vypnuti, color="orange", alpha=0.3,
                   label="cívka zapnutá")
    axs[0].set(xlim=(-45, 45), xlabel="úhel magnetu za cívkou [°]",
               ylabel="k_T [mN·m/A]", title="Momentová konstanta (= zpětné EMF)")
    omegy = np.linspace(5, 1100, 80)
    mom = [mm.ustaleny_cyklus(w, k_t, okno, civka, napajeni, rotor)[0] for w in omegy]
    ot = omegy * 60 / (2 * np.pi)
    axs[1].plot(ot, np.array(mom) * 1e3, label="moment cívky")
    axs[1].plot(ot, treni.moment(omegy) * 1e3, label="ztráty (ložiska + vzduch)")
    axs[1].axvline(provoz.otacky, color="k", ls=":", label=f"provoz {provoz.otacky:.0f} ot/min")
    axs[1].set(xlabel="otáčky [ot/min]", ylabel="průměrný moment [mN·m]")
    _, _, th, proud = mm.ustaleny_cyklus(provoz.omega, k_t, okno, civka, napajeni, rotor)
    axs[2].plot(np.degrees(th), proud)
    axs[2].set(xlabel="úhel v rámci rozteče [°]", ylabel="proud cívkou [A]",
               title=f"Proud při {provoz.otacky:.0f} ot/min")
    for ax in axs:
        ax.grid(alpha=0.3)
    axs[0].legend()
    axs[1].legend()
    fig.tight_layout()
    fig.savefig(VYSTUPY / "3_pulzni_motor.png", dpi=120)
    plt.close(fig)


def pulzni_motor(magnet, rotor) -> list[str]:
    civka, napajeni, treni = mm.Civka(), mm.Napajeni(), mm.Treni()
    k_t = mm.k_t_rotoru(civka, magnet, rotor)
    vysledky = mm.skenuj_okna(k_t, civka, napajeni, rotor, magnet, treni)
    nej_ot = max(p.otacky for _, p in vysledky)
    okno, provoz = max(((o, p) for o, p in vysledky if p.otacky > 0.9 * nej_ot),
                       key=lambda x: x[1].ucinnost)
    graf_motoru(k_t, okno, provoz, civka, napajeni, rotor, treni)
    rozt = 360 / rotor.pocet_magnetu
    uhel_kt = (DEG[np.argmax(k_t)] + rozt / 2) % rozt - rozt / 2
    proud_max = (napajeni.napeti - napajeni.ubytek_spinace) / civka.odpor
    return [
        f"Cívka: {civka.zavitu} z drátu Ø{civka.prumer_dratu * 1e3:.2f} mm, "
        f"{civka.delka_dratu:.1f} m, R = {civka.odpor:.2f} Ω, L = {civka.indukcnost * 1e3:.2f} mH",
        f"Max. proud (stojící rotor) {proud_max:.2f} A, "
        f"špičkový moment {np.max(k_t) * proud_max * 1e3:.1f} mN·m",
        f"k_T max = {np.max(k_t) * 1e3:.2f} mN·m/A v úhlu {uhel_kt:.1f}° za úvratí",
        f"Moment setrvačnosti rotoru J = {rotor.moment_setrvacnosti(magnet):.2e} kg·m²",
        f"Doporučené okno: zapnout {okno.zapnuti}° a vypnout {okno.vypnuti}° za úvratí",
        f"Ustálené otáčky ≈ {provoz.otacky:.0f} ot/min, příkon {provoz.prikon:.2f} W, "
        f"mech. výkon {provoz.moment * provoz.omega * 1e3:.0f} mW, "
        f"účinnost {provoz.ucinnost * 100:.0f} %",
        f"Odstředivá síla na 1 magnet ≈ {magnet.hmotnost * provoz.omega**2 * rotor.polomer_magnetu:.0f} N "
        f"(drží ji stěna 0,8 mm + lepidlo)",
        f"Roztočení na 90 % otáček ≈ {provoz.roztoceni:.1f} s",
        f"Odběr z 6×AA přes regulátor ≈ {z_baterie(provoz.prikon):.2f} W, "
        f"výdrž ≈ {KAPACITA_WH / z_baterie(provoz.prikon):.0f} h",
        "Citlivost (stejné okno):",
    ] + citlivost(k_t, okno, civka, rotor, magnet, treni), k_t, okno


KAPACITA_WH = 6 * 1.5 * 2.5        # 6x AA alkalické, ~2,5 Ah
UCINNOST_MENICE = 0.85             # step-down LM2596
PRIKON_LOGIKY = 0.05               # Hallova sonda, pull-upy, LED [W] při 9 V


def z_baterie(prikon_civky: float) -> float:
    return prikon_civky / UCINNOST_MENICE + PRIKON_LOGIKY


def citlivost(k_t, okno, civka, rotor, magnet, treni) -> list[str]:
    n38 = mm.Magnet(br=1.23)
    varianty = {
        "BEZ Zenerovy diody (jen dioda)": (mm.Napajeni(ubytek_diody=0.7), treni, k_t, magnet),
        "magnety N38 místo N50": (mm.Napajeni(), treni, mm.k_t_rotoru(civka, n38, rotor), n38),
        "tření 2× menší": (mm.Napajeni(), mm.Treni(treni.staticke / 2, treni.viskozni / 2),
                           k_t, magnet),
        "tření 2× větší": (mm.Napajeni(), mm.Treni(treni.staticke * 2, treni.viskozni * 2),
                           k_t, magnet),
    }
    radky = []
    for nazev, (nap, tr, kt, mag) in varianty.items():
        p = mm.najdi_provoz(kt, okno, civka, nap, rotor, mag, tr)
        radky.append(f"  {nazev}: " + ("nerozběhne se" if p is None else
                     f"{p.otacky:.0f} ot/min, {p.prikon:.2f} W, účinnost {p.ucinnost * 100:.0f} %"))
    return radky


NAPETI_REGULATORU = [2.2, 3.0, 4.0, 5.0, 6.0]   # rozsah potenciometru 2,2-6,0 V


def regulace_a_vykon(k_t, okno, magnet, rotor) -> list[str]:
    """Otáčky naprázdno a maximální užitečný výkon pro polohy regulátoru."""
    civka, treni = mm.Civka(), mm.Treni()
    radky, body = [], []
    for u in NAPETI_REGULATORU:
        nap = mm.Napajeni(napeti=u)
        p = mm.najdi_provoz(k_t, okno, civka, nap, rotor, magnet, treni)
        v = mm.max_uzitecny_vykon(k_t, okno, civka, nap, rotor, treni)
        if p is None or v is None:
            radky.append(f"  {u:.1f} V: nerozběhne se")
            continue
        body.append((u, p, v))
        radky.append(
            f"  {u:.1f} V: naprázdno {p.otacky:5.0f} ot/min, z baterie {z_baterie(p.prikon):.2f} W | "
            f"MAX VÝKON {v.vykon * 1e3:5.0f} mW při {v.otacky:4.0f} ot/min, "
            f"moment {v.moment * 1e3:.2f} mN·m, účinnost cívky {v.ucinnost * 100:.0f} %, "
            f"z baterie {z_baterie(v.prikon):.2f} W")
    graf_regulace(k_t, okno, magnet, rotor, body)
    return radky


def graf_regulace(k_t, okno, magnet, rotor, body) -> None:
    civka, treni = mm.Civka(), mm.Treni()
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 8))
    for u in NAPETI_REGULATORU:
        nap = mm.Napajeni(napeti=u)
        omegy = np.linspace(5, 900, 120)
        p_uz = [(mm.ustaleny_cyklus(w, k_t, okno, civka, nap, rotor)[0]
                 - treni.moment(w)) * w for w in omegy]
        ax1.plot(omegy * 60 / (2 * np.pi), np.maximum(p_uz, 0) * 1e3, label=f"{u:.1f} V")
    ax1.set(xlabel="otáčky [ot/min]", ylabel="užitečný výkon na hřídeli [mW]",
            title="Výkon podle polohy regulátoru (napětí cívky)")
    ax1.legend()
    u = [b[0] for b in body]
    ax2.plot(u, [b[1].otacky for b in body], "o-", label="otáčky naprázdno")
    ax2.set(xlabel="napětí cívky z regulátoru [V]", ylabel="otáčky [ot/min]")
    ax3 = ax2.twinx()
    ax3.plot(u, [b[2].vykon * 1e3 for b in body], "s--", color="C3", label="max. výkon")
    ax3.set_ylabel("max. užitečný výkon [mW]", color="C3")
    for ax in (ax1, ax2):
        ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(VYSTUPY / "5_regulace_a_vykon.png", dpi=120)
    plt.close(fig)


def main() -> None:
    VYSTUPY.mkdir(exist_ok=True)
    magnet, rotor = mm.Magnet(), mm.Rotor()
    radky_motoru, k_t, okno = pulzni_motor(magnet, rotor)
    sekce = {
        "MAGNET": graf_pole(magnet) + [f"Hmotnost magnetu {magnet.hmotnost * 1e3:.2f} g"],
        "ROTOR JEN S MAGNETY (bez napájení)": scenare_bez_napajeni(magnet, rotor),
        "PULZNÍ MOTOR (cívka + Hallova sonda, 6 V z regulátoru)": radky_motoru,
        "REGULÁTOR OTÁČEK A VÝKON": regulace_a_vykon(k_t, okno, magnet, rotor),
    }
    text = "\n\n".join(f"== {k} ==\n" + "\n".join(v) for k, v in sekce.items())
    (VYSTUPY / "vysledky.txt").write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
