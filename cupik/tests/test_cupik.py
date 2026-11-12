"""Testy firmwaru Cupíka – spouští se v běžném Pythonu bez robota:

    python3 -m unittest discover -s cupik/tests
"""
import asyncio
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "firmware"))

from cupik import chuze, program, servo, nastaveni, web  # noqa: E402
from cupik.robot import Robot, DOMU  # noqa: E402


class FalesneServo:
    def __init__(self):
        self.trim, self.smer, self.historie = 0, 1, []

    def nastav(self, uhel):
        self.historie.append(uhel)


class FalesnyBzucak:
    def __init__(self):
        self.tony = []

    def ton(self, f):
        self.tony.append(f)

    def ticho(self):
        pass


def novy_robot(rychlost=2.5):
    data = nastaveni.over({"rychlost": rychlost})
    return Robot([FalesneServo() for _ in range(4)], data, FalesnyBzucak())


class TestChuze(unittest.TestCase):
    def test_vpred_v_case_nula_ma_kycle_rovne_a_kotniky_naklopene(self):
        u = chuze.uhly("vpred", 0)
        self.assertAlmostEqual(u[0], 0)
        self.assertAlmostEqual(u[2], -20)

    def test_obraceny_smer_chuze_prohodi_naklon_kotniku(self):
        self.assertAlmostEqual(chuze.uhly("vpred", 0, smer_chuze=-1)[2], 20)

    def test_uhly_nikdy_neprekroci_bezpecny_rozsah(self):
        for nazev in chuze.POHYBY:
            for t in range(0, 2000, 37):
                for u in chuze.uhly(nazev, t, rychlost=2.5):
                    self.assertLessEqual(abs(u), chuze.MAX_UHEL)

    def test_pohyb_je_periodicky(self):
        p = chuze.perioda_ms("tanec")
        for a, b in zip(chuze.uhly("tanec", 123), chuze.uhly("tanec", 123 + p)):
            self.assertAlmostEqual(a, b, places=6)

    def test_otoceni_vlevo_ma_vetsi_kmit_leve_kycle(self):
        amp = chuze.POHYBY["vlevo"][0]
        self.assertGreater(amp[chuze.KYCEL_L], amp[chuze.KYCEL_P])

    def test_neznamy_pohyb_vyhodi_chybu(self):
        with self.assertRaises(ValueError):
            chuze.uhly("salto", 0)

    def test_prolni_vraci_krajni_hodnoty(self):
        self.assertEqual(chuze.prolni((0, 0), (10, -10), 0), (0, 0))
        self.assertEqual(chuze.prolni((0, 0), (10, -10), 1), (10, -10))
        self.assertEqual(chuze.prolni((0, 0), (10, -10), 2), (10, -10))


class TestProgram(unittest.TestCase):
    def test_rozbali_vnorena_opakovani(self):
        prg = [{"p": "vpred", "n": 2},
               {"p": "opakuj", "n": 2, "telo": [{"p": "tanec", "n": 1}, {"p": "pipni", "n": 1}]}]
        program.over(prg)
        self.assertEqual(program.rozbal(prg),
                         [("vpred", 2), ("tanec", 1), ("pipni", 1), ("tanec", 1), ("pipni", 1)])

    def test_odmitne_neznamy_prikaz(self):
        with self.assertRaises(program.ChybaProgramu):
            program.over([{"p": "import os"}])

    def test_odmitne_spatny_pocet(self):
        for n in (0, 21, "3", True, 1.5):
            with self.assertRaises(program.ChybaProgramu):
                program.over([{"p": "vpred", "n": n}])

    def test_odmitne_prilis_hluboka_opakovani(self):
        prg = [{"p": "vpred"}]
        for _ in range(4):
            prg = [{"p": "opakuj", "n": 2, "telo": prg}]
        with self.assertRaises(program.ChybaProgramu):
            program.over(prg)

    def test_odmitne_program_ktery_by_bezel_moc_dlouho(self):
        prg = [{"p": "opakuj", "n": 20, "telo": [{"p": "opakuj", "n": 20, "telo": [{"p": "vpred", "n": 2}]}]}]
        with self.assertRaises(program.ChybaProgramu):
            program.over(prg)

    def test_odmitne_program_ktery_neni_seznam(self):
        for spatny in (None, {}, "vpred", [1]):
            with self.assertRaises(program.ChybaProgramu):
                program.over(spatny)


class TestServo(unittest.TestCase):
    def test_stred(self):
        self.assertEqual(servo.uhel_na_us(0), 1500)

    def test_smer_a_trim(self):
        self.assertEqual(servo.uhel_na_us(45, smer=1), 2000)
        self.assertEqual(servo.uhel_na_us(45, smer=-1), 1000)
        self.assertEqual(servo.uhel_na_us(0, trim=9), 1600)

    def test_omezeni_na_bezpecny_rozsah(self):
        self.assertEqual(servo.uhel_na_us(500), servo.MAX_US)
        self.assertEqual(servo.uhel_na_us(-500), servo.MIN_US)


class TestNastaveni(unittest.TestCase):
    def test_doplni_vychozi_hodnoty(self):
        self.assertEqual(nastaveni.over({}), nastaveni.VYCHOZI)

    def test_odmitne_spatne_hodnoty(self):
        for spatne in ({"trim": [0, 0, 0]}, {"trim": [99, 0, 0, 0]}, {"smer": [1, 2, 1, 1]},
                       {"smer_chuze": 0}, {"rychlost": 10}, [], {"trim": [True, 0, 0, 0]}):
            with self.assertRaises(nastaveni.ChybaNastaveni):
                nastaveni.over(spatne)

    def test_ulozi_a_nacte(self):
        with tempfile.TemporaryDirectory() as d:
            soubor = os.path.join(d, "n.json")
            nastaveni.uloz({"trim": [1, -2, 3, -4]}, soubor)
            self.assertEqual(nastaveni.nacti(soubor)["trim"], [1, -2, 3, -4])

    def test_poskozeny_soubor_vrati_vychozi(self):
        with tempfile.TemporaryDirectory() as d:
            soubor = os.path.join(d, "n.json")
            with open(soubor, "w") as f:
                f.write("{nesmysl")
            self.assertEqual(nastaveni.nacti(soubor), nastaveni.VYCHOZI)
            self.assertEqual(nastaveni.nacti(os.path.join(d, "neni.json")), nastaveni.VYCHOZI)


class TestRobot(unittest.TestCase):
    def test_provede_program_a_vrati_se_domu(self):
        r = novy_robot()
        asyncio.run(r.proved([("vpred", 1), ("pipni", 2)]))
        self.assertEqual(r.poloha, DOMU)
        self.assertFalse(r.bezi)
        self.assertGreater(len(r.serva[0].historie), 10)
        self.assertEqual(len(r.bzucak.tony), 2)

    def test_stop_ukonci_program_rychle(self):
        r = novy_robot(rychlost=0.3)

        async def scenar():
            uloha = asyncio.create_task(r.proved([("tanec", 20)]))
            await asyncio.sleep(0.15)
            self.assertTrue(r.bezi)
            r.zastav()
            await asyncio.wait_for(uloha, 1.0)

        asyncio.run(scenar())
        self.assertFalse(r.bezi)
        self.assertEqual(r.poloha, DOMU)

    def test_kalibrace_preda_trim_a_smer_servum(self):
        r = novy_robot()
        r.nastav(nastaveni.over({"trim": [5, 0, 0, 0], "smer": [-1, 1, 1, 1]}))
        self.assertEqual((r.serva[0].trim, r.serva[0].smer), (5, -1))

    def test_kloub_je_omezen(self):
        r = novy_robot()
        r.kloub(2, 200)
        self.assertEqual(r.poloha[2], chuze.MAX_UHEL)


class TestWeb(unittest.TestCase):
    def setUp(self):
        self.adresar = tempfile.TemporaryDirectory()
        cesta = lambda n: os.path.join(self.adresar.name, n)  # noqa: E731
        self.app = web.Aplikace(novy_robot(), cesta("program.json"), cesta("nastaveni.json"))

    def tearDown(self):
        self.adresar.cleanup()

    def dotaz(self, metoda, cesta, data=None):
        async def proved():
            telo = json.dumps(data) if data is not None else ""
            status, _, odp = await self.app.zpracuj(metoda, cesta, telo)
            if self.app.uloha:
                self.app.robot.zastav()
                await self.app.uloha
            return status, json.loads(odp)
        return asyncio.run(proved())

    def test_stav(self):
        status, odp = self.dotaz("GET", "/api/stav")
        self.assertEqual(status, 200)
        self.assertTrue(odp["ok"])
        self.assertIn("vpred", odp["data"]["pohyby"])

    def test_spust_platny_program(self):
        status, odp = self.dotaz("POST", "/api/spust", {"program": [{"p": "vpred", "n": 1}]})
        self.assertEqual((status, odp["ok"]), (200, True))

    def test_spust_odmitne_spatny_program(self):
        status, odp = self.dotaz("POST", "/api/spust", {"program": [{"p": "letej"}]})
        self.assertEqual(status, 400)
        self.assertIn("neznámý", odp["chyba"])

    def test_druhe_spusteni_behem_behu_je_odmitnuto(self):
        async def scenar():
            prg = json.dumps({"program": [{"p": "tanec", "n": 5}]})
            prvni = await self.app.zpracuj("POST", "/api/spust", prg)
            druhy = await self.app.zpracuj("POST", "/api/spust", prg)
            kloub = await self.app.zpracuj("POST", "/api/kloub", json.dumps({"kloub": 0, "uhel": 10}))
            self.app.robot.zastav()
            await self.app.uloha
            return prvni[0], druhy[0], kloub[0]
        self.assertEqual(asyncio.run(scenar()), (200, 409, 409))

    def test_ulozeny_program_se_nacte_ve_stavu(self):
        prg = [{"p": "tanec", "n": 3}]
        self.dotaz("POST", "/api/uloz", {"program": prg})
        _, odp = self.dotaz("GET", "/api/stav")
        self.assertEqual(odp["data"]["program"], prg)

    def test_nastaveni_se_ulozi_a_spatne_odmitne(self):
        status, odp = self.dotaz("POST", "/api/nastaveni", {"trim": [1, 2, 3, 4]})
        self.assertEqual(status, 200)
        self.assertEqual(self.app.robot.serva[3].trim, 4)
        status, _ = self.dotaz("POST", "/api/nastaveni", {"trim": "ahoj"})
        self.assertEqual(status, 400)

    def test_spatny_json_a_neznama_cesta(self):
        async def scenar():
            return (await self.app.zpracuj("POST", "/api/spust", "{nesmysl"))[0], \
                   (await self.app.zpracuj("GET", "/tajne", ""))[0], \
                   (await self.app.zpracuj("DELETE", "/api/stav", ""))[0]
        self.assertEqual(asyncio.run(scenar()), (400, 404, 405))

    def test_kloub_odmitne_spatna_data(self):
        for data in ({"kloub": 7, "uhel": 0}, {"kloub": 0, "uhel": "x"}, {"kloub": True, "uhel": 0}):
            status, _ = self.dotaz("POST", "/api/kloub", data)
            self.assertEqual(status, 400)

    def test_http_server_odpovi_a_odmitne_velke_telo(self):
        async def scenar():
            srv = await web.server(self.app, port=0)
            port = srv.sockets[0].getsockname()[1]

            async def posli(pozadavek):
                r, w = await asyncio.open_connection("127.0.0.1", port)
                w.write(pozadavek)
                await w.drain()
                odp = await r.read()
                w.close()
                return odp.decode()

            stav = await posli(b"GET /api/stav HTTP/1.1\r\nHost: x\r\n\r\n")
            velke = await posli(b"POST /api/spust HTTP/1.1\r\nContent-Length: 999999\r\n\r\n")
            srv.close()
            await srv.wait_closed()
            return stav, velke
        stav, velke = asyncio.run(scenar())
        self.assertTrue(stav.startswith("HTTP/1.0 200"))
        self.assertIn('"ok": true', stav)
        self.assertTrue(velke.startswith("HTTP/1.0 413"))


if __name__ == "__main__":
    unittest.main()
