# Cupík – robot: pohyby, zvuky a senzor vzdálenosti
#
# Použití v Thonny (MicroPython):
#     from cupik.robot import robot
#     r = robot()
#     r.vpred(3)
#     r.vlevo(2)
#     r.tanec()
#     r.pipni()

import asyncio
from cupik import chuze

try:
    from time import ticks_ms, ticks_diff
except ImportError:  # běžný Python (testy)
    import time

    def ticks_ms():
        return int(time.monotonic() * 1000)

    def ticks_diff(a, b):
        return a - b

SNIMEK_MS = 20       # jak často se přepočítá poloha serv
PRECHOD_MS = 200     # plynulý přechod do první polohy pohybu
DOMU = (0, 0, 0, 0)

MELODIE = ((523, 150), (659, 150), (784, 150), (1047, 300))


async def _spi(ms):
    if hasattr(asyncio, "sleep_ms"):
        await asyncio.sleep_ms(ms)
    else:
        await asyncio.sleep(ms / 1000)


class Robot:
    def __init__(self, serva, nastaveni, bzucak=None, dalkomer=None):
        self.serva = serva
        self.bzucak = bzucak
        self.dalkomer = dalkomer
        self.poloha = DOMU
        self.bezi = False
        self._stop = False
        self.nastav(nastaveni)

    # ---------- nastavení a kalibrace ----------
    def nastav(self, nastaveni):
        self.nastaveni = nastaveni
        for servo, trim, smer in zip(self.serva, nastaveni["trim"], nastaveni["smer"]):
            servo.trim = trim
            servo.smer = smer

    def _nastav_polohu(self, uhly):
        for servo, uhel in zip(self.serva, uhly):
            servo.nastav(uhel)
        self.poloha = tuple(uhly)

    def kloub(self, cislo, uhel):
        """Natočí jeden kloub (pro kalibraci)."""
        uhly = list(self.poloha)
        uhly[cislo] = chuze.omez(uhel)
        self._nastav_polohu(uhly)

    def zastav(self):
        self._stop = True

    # ---------- pohyby (async) ----------
    async def prejdi(self, cil, ms=PRECHOD_MS):
        start = self.poloha
        kroku = max(1, ms // SNIMEK_MS)
        for i in range(1, kroku + 1):
            if self._stop:
                return
            self._nastav_polohu(chuze.prolni(start, cil, i / kroku))
            await _spi(SNIMEK_MS)

    async def pohyb(self, nazev, kroky=1):
        rychlost = self.nastaveni["rychlost"]
        smer = self.nastaveni["smer_chuze"]
        await self.prejdi(chuze.uhly(nazev, 0, rychlost, smer))
        delka = chuze.perioda_ms(nazev, rychlost) * kroky
        start = ticks_ms()
        while not self._stop:
            t = ticks_diff(ticks_ms(), start)
            if t >= delka:
                break
            self._nastav_polohu(chuze.uhly(nazev, t, rychlost, smer))
            await _spi(SNIMEK_MS)

    async def _domu(self):
        await self.prejdi(DOMU, 300)

    async def _pipni(self, ton=880, ms=150):
        if self.bzucak:
            self.bzucak.ton(ton)
        await _spi(ms)
        if self.bzucak:
            self.bzucak.ticho()
        await _spi(50)

    async def _melodie(self):
        for ton, ms in MELODIE:
            if self._stop:
                break
            await self._pipni(ton, ms)

    async def _cekej(self, sekundy=1):
        konec = sekundy * 1000
        start = ticks_ms()
        while not self._stop and ticks_diff(ticks_ms(), start) < konec:
            await _spi(SNIMEK_MS)

    async def proved(self, kroky):
        """Provede rozbalený program: seznam dvojic (příkaz, počet)."""
        self._stop = False
        self.bezi = True
        try:
            for prikaz, n in kroky:
                if self._stop:
                    break
                await self._jeden(prikaz, n)
        finally:
            self._stop = False
            await self._domu()
            self.bezi = False

    async def _jeden(self, prikaz, n):
        if prikaz in chuze.POHYBY:
            await self.pohyb(prikaz, n)
        elif prikaz == "pipni":
            for _ in range(n):
                await self._pipni()
        elif prikaz == "melodie":
            for _ in range(n):
                await self._melodie()
        elif prikaz == "cekej":
            await self._cekej(n)
        elif prikaz == "domu":
            await self._domu()
        else:
            raise ValueError("neznámý příkaz: %s" % prikaz)

    # ---------- senzor ----------
    def vzdalenost(self):
        """Vzdálenost překážky v cm, nebo -1 když nic nevidí."""
        if self.dalkomer is None:
            return -1
        return self.dalkomer.cm()

    # ---------- jednoduché příkazy pro Thonny (blokují) ----------
    def _spust(self, prikaz, n=1):
        asyncio.run(self.proved([(prikaz, n)]))

    def vpred(self, n=1): self._spust("vpred", n)
    def vzad(self, n=1): self._spust("vzad", n)
    def vlevo(self, n=1): self._spust("vlevo", n)
    def vpravo(self, n=1): self._spust("vpravo", n)
    def houpej(self, n=1): self._spust("houpej", n)
    def pruz(self, n=1): self._spust("pruz", n)
    def tanec(self, n=1): self._spust("tanec", n)
    def kroc(self, n=1): self._spust("kroc", n)
    def pipni(self, n=1): self._spust("pipni", n)
    def melodie(self, n=1): self._spust("melodie", n)
    def cekej(self, sekundy=1): self._spust("cekej", sekundy)
    def domu(self): self._spust("domu", 1)


def robot():
    """Vytvoří robota podle config.py a uložené kalibrace (jen na ESP32)."""
    from cupik import hw, nastaveni
    return Robot(hw.serva(), nastaveni.nacti(), hw.Bzucak(), hw.Dalkomer())
