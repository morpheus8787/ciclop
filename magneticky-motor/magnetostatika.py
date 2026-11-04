"""Magnetostatické jádro modelu.

Permanentní magnet je nahrazen ekvivalentními povrchovými proudy
(Ampérův model): kvádr zmagnetovaný podél tloušťky L se chová jako
plošný proud K = Br / mu0 obtékající jeho boční stěny. Ten rozdělíme
na n_vrstev obdélníkových smyček, každá nese proud Br*L/(mu0*n).

Pole počítáme přesným Biot-Savartovým vzorcem pro konečný přímý úsek,
sílu na vodiče F = I dl x B. Všechny délky jsou v metrech.
"""

from dataclasses import dataclass

import numpy as np

MU0 = 4e-7 * np.pi
_EPS = 1e-12           # ochrana proti dělení nulou
_CHUNK = 512           # počet cílových bodů zpracovaných najednou


@dataclass(frozen=True)
class Proudovod:
    """Sada přímých úseků: začátky a, konce b (N x 3) a proudy I (N)."""

    a: np.ndarray
    b: np.ndarray
    proud: np.ndarray

    def spoj(self, other: "Proudovod") -> "Proudovod":
        return Proudovod(
            np.vstack([self.a, other.a]),
            np.vstack([self.b, other.b]),
            np.concatenate([self.proud, other.proud]),
        )

    def zjemni(self, n: int) -> "Proudovod":
        """Rozdělí každý úsek na n kratších (pro přesnější výpočet síly)."""
        t = np.linspace(0.0, 1.0, n + 1)
        d = self.b - self.a
        a = (self.a[:, None, :] + t[None, :-1, None] * d[:, None, :]).reshape(-1, 3)
        b = (self.a[:, None, :] + t[None, 1:, None] * d[:, None, :]).reshape(-1, 3)
        return Proudovod(a, b, np.repeat(self.proud, n))


def pole_B(zdroj: Proudovod, body: np.ndarray) -> np.ndarray:
    """Magnetická indukce [T] v bodech (M x 3) od všech úseků zdroje."""
    vysledek = np.zeros_like(body, dtype=float)
    for start in range(0, len(body), _CHUNK):
        p = body[start:start + _CHUNK, None, :]
        r1 = p - zdroj.a[None, :, :]
        r2 = p - zdroj.b[None, :, :]
        n1 = np.linalg.norm(r1, axis=2)
        n2 = np.linalg.norm(r2, axis=2)
        jmen = n1 * n2 * (n1 * n2 + np.einsum("ijk,ijk->ij", r1, r2))
        koef = zdroj.proud[None, :] * (n1 + n2) / (jmen + _EPS)
        vysledek[start:start + _CHUNK] = (
            MU0 / (4 * np.pi) * np.einsum("ij,ijk->ik", koef, np.cross(r1, r2))
        )
    return vysledek


def sila_a_moment(cil: Proudovod, zdroj: Proudovod) -> tuple[np.ndarray, float]:
    """Celková síla [N] a moment k ose z [N.m] na vodiče `cil` v poli `zdroj`."""
    stred = 0.5 * (cil.a + cil.b)
    dl = cil.b - cil.a
    dF = cil.proud[:, None] * np.cross(dl, pole_B(zdroj, stred))
    moment_z = np.sum(stred[:, 0] * dF[:, 1] - stred[:, 1] * dF[:, 0])
    return dF.sum(axis=0), float(moment_z)


def _do_globalnich(lok: np.ndarray, uhel: float, polomer: float) -> np.ndarray:
    """Lokální soustava (x radiálně ven, y tečně, z osa) -> globální."""
    c, s = np.cos(uhel), np.sin(uhel)
    x = polomer + lok[:, 0]
    return np.column_stack([c * x - s * lok[:, 1], s * x + c * lok[:, 1], lok[:, 2]])


def magnet_kvadr(
    sirka: float,
    vyska: float,
    tloustka: float,
    br: float,
    uhel: float,
    polomer_stredu: float,
    smer: int = 1,
    n_vrstev: int = 6,
) -> Proudovod:
    """Kvádrový magnet zmagnetovaný radiálně (podél tloušťky).

    sirka  - rozměr v tečném směru, vyska - rozměr podél osy rotoru z,
    smer   - +1 = severní pól směřuje ven od osy, -1 = dovnitř.
    """
    hw, hh = sirka / 2, vyska / 2
    roh = np.array([[-hw, -hh], [hw, -hh], [hw, hh], [-hw, hh]])
    if smer < 0:
        roh = roh[::-1]
    proud_vrstvy = br * tloustka / (MU0 * n_vrstev)
    xs = (np.arange(n_vrstev) + 0.5) / n_vrstev * tloustka - tloustka / 2
    a_list, b_list = [], []
    for x in xs:
        body = np.column_stack([np.full(4, x), roh])
        a_list.append(body)
        b_list.append(np.roll(body, -1, axis=0))
    a = _do_globalnich(np.vstack(a_list), uhel, polomer_stredu)
    b = _do_globalnich(np.vstack(b_list), uhel, polomer_stredu)
    return Proudovod(a, b, np.full(len(a), proud_vrstvy))


def civka_valcova(
    r_vnitrni: float,
    r_vnejsi: float,
    delka: float,
    zavitu: int,
    uhel: float,
    polomer_stredu: float,
    n_radial: int = 4,
    n_axial: int = 5,
    n_segmentu: int = 48,
) -> Proudovod:
    """Vzduchová cívka s osou radiálně k rotoru; proud 1 A v drátu.

    Kladný proud vytváří pole směřující ven od osy rotoru (+x lokálně).
    """
    rs = r_vnitrni + (np.arange(n_radial) + 0.5) / n_radial * (r_vnejsi - r_vnitrni)
    xs = (np.arange(n_axial) + 0.5) / n_axial * delka - delka / 2
    fi = np.linspace(0, 2 * np.pi, n_segmentu + 1)
    proud = zavitu / (n_radial * n_axial)
    a_list, b_list = [], []
    for r in rs:
        for x in xs:
            body = np.column_stack([np.full_like(fi, x), r * np.cos(fi), r * np.sin(fi)])
            a_list.append(body[:-1])
            b_list.append(body[1:])
    a = _do_globalnich(np.vstack(a_list), uhel, polomer_stredu)
    b = _do_globalnich(np.vstack(b_list), uhel, polomer_stredu)
    return Proudovod(a, b, np.full(len(a), proud))


def pole_na_ose_analyticky(
    sirka: float, vyska: float, tloustka: float, br: float, z: float
) -> float:
    """Přesné pole Bz na ose kvádrového magnetu ve vzdálenosti z od plochy."""

    def clen(d: float) -> float:
        return np.arctan(
            sirka * vyska / (2 * d * np.sqrt(4 * d**2 + sirka**2 + vyska**2))
        )

    return br / np.pi * (clen(z) - clen(z + tloustka))
