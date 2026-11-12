# Cupík – kontrola a rozbalení dětských programů
#
# Program je seznam příkazů, např.:
#   [{"p": "vpred", "n": 3},
#    {"p": "opakuj", "n": 2, "telo": [{"p": "tanec", "n": 1}, {"p": "pipni", "n": 1}]}]
# Před spuštěním se program zkontroluje (nic neznámého, rozumné limity)
# a rozbalí na plochý seznam kroků.

from cupik.chuze import POHYBY

OSTATNI = ("pipni", "cekej", "domu", "melodie")
MAX_N = 20            # nejvíc opakování jednoho příkazu
MAX_PRIKAZU = 60      # nejvíc příkazů v programu
MAX_HLOUBKA = 3       # opakování v opakování v opakování
MAX_KROKU = 400       # nejvíc kroků po rozbalení (ochrana před nekonečným tancem)


class ChybaProgramu(ValueError):
    pass


def _over_prikaz(prikaz, hloubka, pocet):
    if not isinstance(prikaz, dict):
        raise ChybaProgramu("příkaz musí být objekt")
    nazev = prikaz.get("p")
    n = prikaz.get("n", 1)
    if not isinstance(n, int) or isinstance(n, bool) or not 1 <= n <= MAX_N:
        raise ChybaProgramu("počet musí být 1 až %d" % MAX_N)
    if nazev == "opakuj":
        if hloubka >= MAX_HLOUBKA:
            raise ChybaProgramu("moc vnořených opakování")
        return _over_seznam(prikaz.get("telo"), hloubka + 1, pocet)
    if nazev not in POHYBY and nazev not in OSTATNI:
        raise ChybaProgramu("neznámý příkaz: %s" % nazev)
    return pocet + 1


def _over_seznam(seznam, hloubka, pocet):
    if not isinstance(seznam, list):
        raise ChybaProgramu("program musí být seznam příkazů")
    for prikaz in seznam:
        pocet = _over_prikaz(prikaz, hloubka, pocet)
        if pocet > MAX_PRIKAZU:
            raise ChybaProgramu("program je moc dlouhý (max %d příkazů)" % MAX_PRIKAZU)
    return pocet


def over(program):
    """Zkontroluje program. Při chybě vyhodí ChybaProgramu s českou zprávou."""
    _over_seznam(program, 0, 0)
    rozbal(program)  # hlídá i celkovou délku
    return program


def rozbal(program):
    """Převede program na plochý seznam dvojic (příkaz, počet)."""
    vysledek = []
    _rozbal(program, vysledek)
    return vysledek


def _rozbal(seznam, vysledek):
    for prikaz in seznam:
        n = prikaz.get("n", 1)
        if prikaz["p"] == "opakuj":
            for _ in range(n):
                _rozbal(prikaz["telo"], vysledek)
        else:
            vysledek.append((prikaz["p"], n))
        if sum(k[1] for k in vysledek) > MAX_KROKU:
            raise ChybaProgramu("program by běžel moc dlouho (max %d kroků)" % MAX_KROKU)
