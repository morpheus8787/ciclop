# Cupík – výpočet pohybů (běží v MicroPythonu i v běžném Pythonu)
#
# Každý pohyb je sada čtyř „kmitů“ – pro každý kloub jedna sinusovka:
#     úhel = posun + amplituda * sin(2π * t / perioda + fáze)
# Pořadí kloubů: kyčel L, kyčel P, kotník L, kotník P.
#
# Konvence úhlů (stejná pro obě nohy, převod na servo řeší kalibrace):
#   kyčel  + = špička nohy se natočí doleva (při pohledu shora)
#   kotník + = chodidlo se naklopí doprava (při pohledu zepředu)

import math

KYCEL_L, KYCEL_P, KOTNIK_L, KOTNIK_P = 0, 1, 2, 3
POCET_KLOUBU = 4
MAX_UHEL = 60  # bezpečný rozsah kloubů ve stupních

# název: (amplitudy, posuny, fáze ve stupních, perioda v ms)
POHYBY = {
    "vpred":  ((25, 25, 20, 20), (0, 0, 0, 0), (0, 0, -90, -90), 1200),
    "vzad":   ((25, 25, 20, 20), (0, 0, 0, 0), (0, 0, 90, 90), 1200),
    "vlevo":  ((25, 8, 20, 20), (0, 0, 0, 0), (0, 0, -90, -90), 1200),
    "vpravo": ((8, 25, 20, 20), (0, 0, 0, 0), (0, 0, -90, -90), 1200),
    "houpej": ((0, 0, 20, 20), (0, 0, 0, 0), (0, 0, 0, 0), 1000),
    "pruz":   ((0, 0, 20, 20), (0, 0, 0, 0), (0, 0, 90, -90), 800),
    "tanec":  ((25, 25, 15, 15), (0, 0, 0, 0), (0, 0, 90, -90), 1000),
    "kroc":   ((0, 0, 20, 20), (0, 0, 0, 0), (0, 0, 0, 0), 600),
}

NAZVY = {
    "vpred": "Krok dopředu",
    "vzad": "Krok dozadu",
    "vlevo": "Otoč se doleva",
    "vpravo": "Otoč se doprava",
    "houpej": "Houpej se",
    "pruz": "Pružení",
    "tanec": "Tanec",
    "kroc": "Cupitání na místě",
}


def omez(hodnota, mez=MAX_UHEL):
    """Omezí úhel do bezpečného rozsahu ±mez."""
    if hodnota > mez:
        return mez
    if hodnota < -mez:
        return -mez
    return hodnota


def uhly(nazev, t_ms, rychlost=1.0, smer_chuze=1):
    """Vrátí n-tici čtyř úhlů pro pohyb `nazev` v čase `t_ms`.

    rychlost > 1 zrychlí pohyb, smer_chuze = -1 prohodí dopředu a dozadu
    (pro případ, že robot po sestavení chodí obráceně).
    """
    if nazev not in POHYBY:
        raise ValueError("neznámý pohyb: " + str(nazev))
    amp, posun, faze, perioda = POHYBY[nazev]
    zaklad = 2 * math.pi * t_ms * rychlost / perioda
    vysledek = []
    for i in range(POCET_KLOUBU):
        f = faze[i] * smer_chuze if i >= KOTNIK_L else faze[i]
        u = posun[i] + amp[i] * math.sin(zaklad + math.radians(f))
        vysledek.append(omez(u))
    return tuple(vysledek)


def perioda_ms(nazev, rychlost=1.0):
    """Délka jednoho kroku pohybu v milisekundách."""
    return int(POHYBY[nazev][3] / rychlost)


def prolni(odkud, kam, podil):
    """Plynulý přechod mezi dvěma polohami (podil 0..1)."""
    podil = max(0.0, min(1.0, podil))
    return tuple(a + (b - a) * podil for a, b in zip(odkud, kam))
