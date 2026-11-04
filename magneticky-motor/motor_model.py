"""Model zkušebního magnetického motoru z magnetů 20 x 10 x 1,7 mm.

Obsahuje dvě části:
1. Rotor + pevné (statorové) magnety bez napájení -> výpočet momentu
   v každé poloze a práce za otáčku (energetická bilance).
2. Pulzní motor: stejný rotor + vzduchová cívka spínaná Hallovou
   sondou -> momentová konstanta, proud, otáčky, účinnost.
"""

from dataclasses import dataclass

import numpy as np

import magnetostatika as ms

RHO_CU = 1.72e-8          # rezistivita mědi [Ohm.m]
HUSTOTA_NDFEB = 7500.0    # [kg/m3]
HUSTOTA_PLA = 1240.0      # [kg/m3]


@dataclass(frozen=True)
class Magnet:
    sirka: float = 0.010      # tečně [m]
    vyska: float = 0.020      # podél osy rotoru [m]
    tloustka: float = 0.0017  # směr magnetizace [m]
    br: float = 1.29          # remanence N42 [T] (N35 ~ 1.18, N52 ~ 1.43)

    @property
    def hmotnost(self) -> float:
        return self.sirka * self.vyska * self.tloustka * HUSTOTA_NDFEB


@dataclass(frozen=True)
class Rotor:
    polomer_magnetu: float = 0.030   # osa -> střed magnetu [m]
    pocet_magnetu: int = 8
    smer: int = -1                   # -1: jižní pól ven (spíná Hall A3144)
    plneni_pla: float = 0.4          # efektivní hustota tisku

    def uhly(self) -> np.ndarray:
        return np.arange(self.pocet_magnetu) * 2 * np.pi / self.pocet_magnetu

    def moment_setrvacnosti(self, magnet: Magnet) -> float:
        r = self.polomer_magnetu - magnet.tloustka / 2
        h = magnet.vyska + 0.002
        m_disk = np.pi * r**2 * h * HUSTOTA_PLA * self.plneni_pla
        return 0.5 * m_disk * r**2 + self.pocet_magnetu * magnet.hmotnost * self.polomer_magnetu**2


@dataclass(frozen=True)
class Civka:
    r_vnitrni: float = 0.004
    r_vnejsi: float = 0.011
    delka: float = 0.012
    prumer_dratu: float = 0.30e-3    # holá měď
    prumer_izolace: float = 0.34e-3  # s lakem
    cinitel_plneni: float = 0.80
    mezera: float = 0.0025           # čelo magnetu -> čelo vinutí [m] (stěna 0,8 + vůle + čelo kostry)

    @property
    def zavitu(self) -> int:
        plocha = (self.r_vnejsi - self.r_vnitrni) * self.delka
        return int(self.cinitel_plneni * plocha / self.prumer_izolace**2)

    @property
    def delka_dratu(self) -> float:
        return self.zavitu * np.pi * (self.r_vnitrni + self.r_vnejsi)

    @property
    def odpor(self) -> float:
        return RHO_CU * self.delka_dratu / (np.pi * self.prumer_dratu**2 / 4)

    @property
    def indukcnost(self) -> float:
        """Wheelerův vzorec pro vícevrstvou vzduchovou cívku [H]."""
        palec = 0.0254
        r = (self.r_vnitrni + self.r_vnejsi) / 2 / palec
        l, c = self.delka / palec, (self.r_vnejsi - self.r_vnitrni) / palec
        return 0.8 * r**2 * self.zavitu**2 / (6 * r + 9 * l + 10 * c) * 1e-6


@dataclass(frozen=True)
class Napajeni:
    napeti: float = 6.0          # 4x AA
    ubytek_spinace: float = 0.1  # logický MOSFET
    # Nulová větev přes cívku: dioda 1N4148/1N4007 (0,7 V) + Zener 15 V v sérii.
    # Samotná dioda by zkratovala napětí indukované přibližujícím se magnetem
    # a cívka by rotor brzdila jako generátor (viz citlivostní rozbor).
    ubytek_diody: float = 15.7


@dataclass(frozen=True)
class Treni:
    staticke: float = 0.4e-3     # dvě ložiska 608ZZ [N.m]
    viskozni: float = 2e-7       # ložiska + vzduch [N.m.s/rad]

    def moment(self, omega: np.ndarray) -> np.ndarray:
        return self.staticke + self.viskozni * omega


UHLY = np.linspace(-np.pi, np.pi, 1441)[:-1]   # krok 0,25°


def moment_na_magnet_rotoru(magnet: Magnet, rotor: Rotor, zdroj: ms.Proudovod,
                            uhly: np.ndarray = UHLY) -> np.ndarray:
    """Moment [N.m] na JEDEN magnet rotoru v poloze theta od zdroje."""
    vysledek = np.empty(len(uhly))
    for i, th in enumerate(uhly):
        mag = ms.magnet_kvadr(magnet.sirka, magnet.vyska, magnet.tloustka, magnet.br,
                              th, rotor.polomer_magnetu, rotor.smer).zjemni(8)
        vysledek[i] = ms.sila_a_moment(mag, zdroj)[1]
    return vysledek


def superpozice(moment_1: np.ndarray, rotor: Rotor, uhly: np.ndarray = UHLY) -> np.ndarray:
    """Moment na celý rotor: součet přes všechny magnety (periodicky)."""
    krok = uhly[1] - uhly[0]
    celkem = np.zeros_like(moment_1)
    for fi in rotor.uhly():
        celkem += np.roll(moment_1, int(round(fi / krok)))
    return celkem


def stator_magnety(magnet: Magnet, rotor: Rotor, uhly_st, mezery, odpudivy=True):
    """Pevné magnety vně rotoru čelem k němu (radiálně)."""
    smer = -rotor.smer if odpudivy else rotor.smer
    zdroj = None
    for fi, g in zip(uhly_st, mezery):
        r = rotor.polomer_magnetu + magnet.tloustka + g
        m = ms.magnet_kvadr(magnet.sirka, magnet.vyska, magnet.tloustka, magnet.br, fi, r, smer)
        zdroj = m if zdroj is None else zdroj.spoj(m)
    return zdroj


def civka_zdroj(civka: Civka, magnet: Magnet, rotor: Rotor) -> ms.Proudovod:
    r = rotor.polomer_magnetu + magnet.tloustka / 2 + civka.mezera + civka.delka / 2
    return ms.civka_valcova(civka.r_vnitrni, civka.r_vnejsi, civka.delka,
                            civka.zavitu, 0.0, r)


def prace_za_otacku(moment: np.ndarray, uhly: np.ndarray = UHLY) -> float:
    """Práce [J] = integrál momentu přes jednu celou otáčku (periodicky)."""
    return float(np.sum(moment) * (uhly[1] - uhly[0]))


@dataclass(frozen=True)
class Okno:
    """Spínací okno cívky ve stupních za horní úvratí (magnet proti cívce)."""
    zapnuti: float
    vypnuti: float


def ustaleny_cyklus(omega: float, k_t: np.ndarray, okno: Okno, civka: Civka,
                    napajeni: Napajeni, rotor: Rotor, uhly: np.ndarray = UHLY):
    """Průběh proudu během jedné rozteče magnetů při konstantních otáčkách.

    Vrací (průměrný moment, příkon z baterie, uhly_cyklu, proud).
    """
    rozt = 2 * np.pi / rotor.pocet_magnetu
    n = 240
    th = np.linspace(0.0, rozt, n, endpoint=False)
    dth = rozt / n
    kt = np.interp(th, uhly, k_t, period=2 * np.pi)
    zap = (th >= np.radians(okno.zapnuti)) & (th < np.radians(okno.vypnuti))
    R, L = civka.odpor, civka.indukcnost
    utlum = np.exp(-R / L * dth / max(omega, 1e-6))
    u = np.where(zap, napajeni.napeti - napajeni.ubytek_spinace, -napajeni.ubytek_diody)
    i_cil = (u - kt * omega) / R
    i = 0.0
    proud = np.empty(n)
    # Dvě rozteče: první ustálí počáteční podmínku, ukládáme druhou.
    # Přesné řešení RL obvodu v kroku; proud nemůže být záporný (dioda).
    for j in list(range(n)) * 2:
        i = max(i_cil[j] + (i - i_cil[j]) * utlum, 0.0)
        proud[j] = i
    moment = float(np.mean(kt * proud))
    prikon = float(np.mean(np.where(zap, napajeni.napeti * proud, 0.0)))
    return moment, prikon, th, proud


@dataclass(frozen=True)
class Provoz:
    omega: float          # ustálená úhlová rychlost [rad/s]
    otacky: float         # [ot/min]
    moment: float         # užitečný moment motoru [N.m]
    prikon: float         # z baterie [W]
    ucinnost: float       # mechanický výkon / příkon
    roztoceni: float      # doba roztočení na 90 % otáček [s]


def najdi_provoz(k_t, okno, civka, napajeni, rotor, magnet, treni) -> Provoz | None:
    """Otáčky, kde moment cívky = moment tření (+ doba roztočení)."""
    omegy = np.linspace(1.0, 1200.0, 160)
    data = [ustaleny_cyklus(w, k_t, okno, civka, napajeni, rotor) for w in omegy]
    netto = np.array([d[0] for d in data]) - treni.moment(omegy)
    if netto[0] <= 0:
        return None
    zaporne = np.nonzero(netto <= 0)[0]
    if len(zaporne) == 0:
        return None
    k = zaporne[0]
    w = omegy[k - 1] + (omegy[k] - omegy[k - 1]) * netto[k - 1] / (netto[k - 1] - netto[k])
    moment, prikon, _, _ = ustaleny_cyklus(w, k_t, okno, civka, napajeni, rotor)
    J = rotor.moment_setrvacnosti(magnet)
    maska = omegy < 0.9 * w
    t = float(np.trapezoid(J / np.maximum(netto[maska], 1e-9), omegy[maska]))
    return Provoz(w, w * 60 / (2 * np.pi), moment, prikon, moment * w / max(prikon, 1e-12), t)


def k_t_rotoru(civka: Civka, magnet: Magnet, rotor: Rotor) -> np.ndarray:
    """Momentová konstanta celého rotoru [N.m/A] (= konstanta zpětného EMF [V.s/rad]).

    Znaménko proudu je zvoleno tak, aby cívka magnet za úvratí odpuzovala.
    """
    k1 = moment_na_magnet_rotoru(magnet, rotor, civka_zdroj(civka, magnet, rotor))
    za_uvrati = np.interp(np.radians(5.0), UHLY, k1)
    return superpozice(k1 * np.sign(za_uvrati), rotor)


def skenuj_okna(k_t, civka, napajeni, rotor, magnet, treni):
    vysledky = []
    for zap in range(0, 9, 2):
        for vyp in range(zap + 6, 25, 2):
            p = najdi_provoz(k_t, Okno(zap, vyp), civka, napajeni, rotor, magnet, treni)
            if p is not None:
                vysledky.append((Okno(zap, vyp), p))
    return vysledky
