"""Kontroly fyzikální správnosti modelu.  Spuštění:  python3 -m pytest -q"""

import numpy as np
import pytest

import magnetostatika as ms
import motor_model as mm

MAGNET = mm.Magnet()
ROTOR = mm.Rotor()
HRUBE_UHLY = np.linspace(-np.pi, np.pi, 361)[:-1]


@pytest.mark.parametrize("z", [0.0005, 0.002, 0.005, 0.010])
def test_pole_na_ose_odpovida_analytickemu_vzorci(z):
    mag = ms.magnet_kvadr(MAGNET.sirka, MAGNET.vyska, MAGNET.tloustka, MAGNET.br, 0, 0)
    bod = np.array([[MAGNET.tloustka / 2 + z, 0.0, 0.0]])
    model = ms.pole_B(mag, bod)[0, 0]
    presne = ms.pole_na_ose_analyticky(MAGNET.sirka, MAGNET.vyska, MAGNET.tloustka,
                                       MAGNET.br, z)
    assert model == pytest.approx(presne, rel=1e-3)


def test_akce_a_reakce_mezi_dvema_magnety():
    a = ms.magnet_kvadr(0.01, 0.02, 0.0017, 1.29, 0.0, 0.03).zjemni(8)
    b = ms.magnet_kvadr(0.01, 0.02, 0.0017, 1.29, 0.2, 0.034).zjemni(8)
    f_ab = ms.sila_a_moment(a, b)[0]
    f_ba = ms.sila_a_moment(b, a)[0]
    assert np.allclose(f_ab, -f_ba, atol=1e-2 * np.linalg.norm(f_ab))


def test_souhlasne_poly_proti_sobe_se_odpuzuji():
    rotor = ms.magnet_kvadr(0.01, 0.02, 0.0017, 1.29, 0.0, 0.03, smer=1).zjemni(8)
    stator = mm.stator_magnety(MAGNET, mm.Rotor(smer=1), [0.0], [0.002], odpudivy=True)
    sila = ms.sila_a_moment(rotor, stator)[0]
    assert sila[0] < 0   # rotorový magnet je tlačen dovnitř k ose


@pytest.mark.parametrize("odpudivy", [True, False])
def test_rotor_jen_s_magnety_nekona_praci_za_otacku(odpudivy):
    zdroj = mm.stator_magnety(MAGNET, ROTOR, np.radians(np.linspace(0, 90, 7)),
                              np.linspace(0.012, 0.002, 7), odpudivy=odpudivy)
    moment = mm.superpozice(
        mm.moment_na_magnet_rotoru(MAGNET, ROTOR, zdroj, HRUBE_UHLY), ROTOR, HRUBE_UHLY)
    prace = mm.prace_za_otacku(moment, HRUBE_UHLY)
    nejvetsi = np.max(np.abs(moment)) * 2 * np.pi
    assert nejvetsi > 1e-3                 # moment existuje a je velký...
    assert abs(prace) < 1e-6 * nejvetsi    # ...ale čistá práce je nulová


def test_parametry_civky():
    civka = mm.Civka()
    assert 500 < civka.zavitu < 700
    assert civka.odpor == pytest.approx(6.7, rel=0.05)
    assert 1e-3 < civka.indukcnost < 5e-3


def test_cyklus_bez_otacek_odpovida_ohmovu_zakonu():
    k_t = np.zeros_like(mm.UHLY)
    okno = mm.Okno(0, 45)
    civka, nap = mm.Civka(), mm.Napajeni()
    _, prikon, _, proud = mm.ustaleny_cyklus(0.001, k_t, okno, civka, nap, ROTOR)
    ocekavany = (nap.napeti - nap.ubytek_spinace) / civka.odpor
    assert proud[-1] == pytest.approx(ocekavany, rel=1e-3)
    assert prikon == pytest.approx(nap.napeti * ocekavany, rel=0.02)


def test_zpetne_emf_omezuje_proud_pri_vysokych_otackach():
    k_t = np.full_like(mm.UHLY, 0.01)
    args = (k_t, mm.Okno(0, 16), mm.Civka(), mm.Napajeni(), ROTOR)
    pomalu = mm.ustaleny_cyklus(10.0, *args)[0]
    rychle = mm.ustaleny_cyklus(500.0, *args)[0]
    assert rychle < pomalu


def test_moment_setrvacnosti_je_realny():
    j = ROTOR.moment_setrvacnosti(MAGNET)
    assert 1e-5 < j < 1e-4
