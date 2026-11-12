# Cupík – uložení kalibrace do souboru nastaveni.json

import json

SOUBOR = "nastaveni.json"
MAX_TRIM = 30

VYCHOZI = {
    "trim": [0, 0, 0, 0],    # korekce serv ve stupních
    "smer": [1, 1, 1, 1],    # +1 nebo -1 pro každé servo
    "smer_chuze": 1,         # -1 když robot chodí obráceně
    "rychlost": 1.0,         # 0.5 = pomalu, 2 = rychle
}


class ChybaNastaveni(ValueError):
    pass


def _seznam_cisel(hodnota, povolene=None, mez=None):
    if not isinstance(hodnota, list) or len(hodnota) != 4:
        raise ChybaNastaveni("čekám seznam čtyř čísel")
    for x in hodnota:
        if not isinstance(x, (int, float)) or isinstance(x, bool):
            raise ChybaNastaveni("hodnota musí být číslo")
        if povolene is not None and x not in povolene:
            raise ChybaNastaveni("směr musí být 1 nebo -1")
        if mez is not None and abs(x) > mez:
            raise ChybaNastaveni("trim musí být v rozsahu ±%d" % mez)
    return list(hodnota)


def over(data):
    """Vrátí nové (zkontrolované) nastavení sloučené s výchozími hodnotami."""
    if not isinstance(data, dict):
        raise ChybaNastaveni("nastavení musí být objekt")
    vysledek = dict(VYCHOZI)
    if "trim" in data:
        vysledek["trim"] = _seznam_cisel(data["trim"], mez=MAX_TRIM)
    if "smer" in data:
        vysledek["smer"] = _seznam_cisel(data["smer"], povolene=(1, -1))
    if "smer_chuze" in data:
        if data["smer_chuze"] not in (1, -1):
            raise ChybaNastaveni("smer_chuze musí být 1 nebo -1")
        vysledek["smer_chuze"] = data["smer_chuze"]
    if "rychlost" in data:
        r = data["rychlost"]
        if not isinstance(r, (int, float)) or isinstance(r, bool) or not 0.3 <= r <= 2.5:
            raise ChybaNastaveni("rychlost musí být 0.3 až 2.5")
        vysledek["rychlost"] = float(r)
    return vysledek


def nacti(soubor=SOUBOR):
    try:
        with open(soubor) as f:
            return over(json.load(f))
    except (OSError, ValueError):
        return dict(VYCHOZI)


def uloz(data, soubor=SOUBOR):
    data = over(data)
    with open(soubor, "w") as f:
        json.dump(data, f)
    return data
