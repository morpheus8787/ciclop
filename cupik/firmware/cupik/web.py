# Cupík – malý webový server pro programování z tabletu
#
# Odpovědi API mají vždy tvar {"ok": true/false, "data": ..., "chyba": ...}

import asyncio
import json
from cupik import program, nastaveni, chuze

MAX_TELO = 4096
SOUBOR_PROGRAMU = "program.json"
SOUBOR_STRANKY = "www/index.html"


def _json(ok, data=None, chyba=None, status=200):
    telo = json.dumps({"ok": ok, "data": data, "chyba": chyba})
    return status, "application/json", telo


def _chyba(zprava, status=400):
    return _json(False, chyba=zprava, status=status)


def _je_cislo(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def nacti_program(soubor=SOUBOR_PROGRAMU):
    try:
        with open(soubor) as f:
            return program.over(json.load(f))
    except (OSError, ValueError):
        return []


class Aplikace:
    def __init__(self, robot, soubor_programu=SOUBOR_PROGRAMU, soubor_nastaveni=nastaveni.SOUBOR):
        self.robot = robot
        self.soubor_programu = soubor_programu
        self.soubor_nastaveni = soubor_nastaveni
        self.uloha = None

    def zaneprazdnen(self):
        # úloha může být vytvořená, ale ještě nezačala běžet -> hlídáme i ji
        return self.robot.bezi or (self.uloha is not None and not self.uloha.done())

    def spust(self, prg):
        """Spustí (už zkontrolovaný) program na pozadí."""
        if self.zaneprazdnen():
            return False
        self.uloha = asyncio.create_task(self.robot.proved(program.rozbal(prg)))
        return True

    async def zpracuj(self, metoda, cesta, telo):
        """Vrátí (status, content-type, tělo odpovědi)."""
        if metoda == "GET":
            return self._get(cesta)
        if metoda != "POST":
            return _chyba("nepodporovaná metoda", 405)
        try:
            data = json.loads(telo) if telo else {}
        except ValueError:
            return _chyba("neplatný JSON")
        try:
            return self._post(cesta, data)
        except ValueError as e:  # ChybaProgramu, ChybaNastaveni
            return _chyba(str(e))

    def _get(self, cesta):
        if cesta == "/api/stav":
            return _json(True, {
                "bezi": self.zaneprazdnen(),
                "program": nacti_program(self.soubor_programu),
                "nastaveni": self.robot.nastaveni,
                "pohyby": chuze.NAZVY,
            })
        if cesta == "/api/vzdalenost":
            return _json(True, {"cm": self.robot.vzdalenost()})
        return _chyba("nenalezeno", 404)

    def _post(self, cesta, data):
        if not isinstance(data, dict):
            return _chyba("čekám objekt")
        if cesta == "/api/spust":
            prg = program.over(data.get("program"))
            if not self.spust(prg):
                return _chyba("robot už něco dělá", 409)
            return _json(True)
        if cesta == "/api/zastav":
            self.robot.zastav()
            return _json(True)
        if cesta == "/api/uloz":
            prg = program.over(data.get("program"))
            with open(self.soubor_programu, "w") as f:
                json.dump(prg, f)
            return _json(True)
        if cesta == "/api/nastaveni":
            nove = nastaveni.uloz(data, self.soubor_nastaveni)
            self.robot.nastav(nove)
            return _json(True, nove)
        if cesta == "/api/kloub":
            return self._kloub(data)
        return _chyba("nenalezeno", 404)

    def _kloub(self, data):
        if self.zaneprazdnen():
            return _chyba("robot právě něco dělá", 409)
        cislo, uhel = data.get("kloub"), data.get("uhel")
        if not _je_cislo(cislo) or cislo not in (0, 1, 2, 3) or not _je_cislo(uhel):
            return _chyba("špatný kloub nebo úhel")
        self.robot.kloub(cislo, uhel)
        return _json(True)


# ---------- HTTP ----------
DUVODY = {200: "OK", 400: "Bad Request", 404: "Not Found", 405: "Method Not Allowed",
          409: "Conflict", 413: "Payload Too Large"}


async def _posli(writer, status, typ, telo):
    if isinstance(telo, str):
        telo = telo.encode()
    hlavicka = "HTTP/1.0 %d %s\r\nContent-Type: %s\r\nContent-Length: %d\r\nConnection: close\r\n\r\n" % (
        status, DUVODY.get(status, ""), typ, len(telo))
    writer.write(hlavicka.encode())
    writer.write(telo)
    await writer.drain()


async def _posli_stranku(writer):
    with open(SOUBOR_STRANKY, "rb") as f:
        stranka = f.read()
    await _posli(writer, 200, "text/html; charset=utf-8", stranka)


async def _obsluz(aplikace, reader, writer):
    try:
        radek = (await reader.readline()).decode()
        casti = radek.split(" ")
        if len(casti) < 2:
            return
        metoda, cesta = casti[0], casti[1].split("?")[0]
        delka = 0
        while True:
            h = await reader.readline()
            if not h or h == b"\r\n":
                break
            if h.lower().startswith(b"content-length:"):
                delka = int(h.split(b":")[1])
        if delka > MAX_TELO:
            await _posli(writer, *_chyba("moc velký požadavek", 413))
            return
        telo = (await reader.readexactly(delka)).decode() if delka else ""
        if metoda == "GET" and cesta in ("/", "/index.html"):
            await _posli_stranku(writer)
        else:
            await _posli(writer, *(await aplikace.zpracuj(metoda, cesta, telo)))
    except Exception as e:  # jeden špatný požadavek nesmí shodit robota
        print("web chyba:", e)
    finally:
        writer.close()
        await writer.wait_closed()


async def server(aplikace, port=80):
    return await asyncio.start_server(lambda r, w: _obsluz(aplikace, r, w), "0.0.0.0", port)
