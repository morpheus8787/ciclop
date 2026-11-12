# Cupík – spouští se automaticky po zapnutí robota
#
# 1. Robot vytvoří Wi-Fi síť „Cupik-XXXX“ (heslo v config.py).
# 2. Na tabletu se připoj a otevři http://192.168.4.1
# 3. Tlačítko BOOT na desce spustí naposledy uložený program.

import asyncio
import machine
import network
import ubinascii
import config
from cupik import web
from cupik.robot import robot as vytvor_robota


def spust_wifi():
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    mac = ubinascii.hexlify(ap.config("mac")).decode()
    nazev = "Cupik-" + mac[-4:].upper()
    ap.config(essid=nazev, password=config.WIFI_HESLO, authmode=network.AUTH_WPA2_PSK)
    print("Wi-Fi:", nazev, " adresa: http://" + ap.ifconfig()[0])
    return nazev


async def hlidej_tlacitko(aplikace):
    tlacitko = machine.Pin(config.PIN_TLACITKO, machine.Pin.IN, machine.Pin.PULL_UP)
    while True:
        if tlacitko.value() == 0:
            if aplikace.zaneprazdnen():
                aplikace.robot.zastav()
            else:
                aplikace.spust(web.nacti_program())
            while tlacitko.value() == 0:  # počkej na puštění
                await asyncio.sleep_ms(20)
        await asyncio.sleep_ms(50)


async def blikej(robot):
    led = machine.Pin(config.PIN_LED, machine.Pin.OUT)
    while True:
        led.value(0 if robot.bezi else 1 - led.value())
        await asyncio.sleep_ms(500)


async def hlavni():
    r = vytvor_robota()
    await r._domu()
    aplikace = web.Aplikace(r)
    spust_wifi()
    await web.server(aplikace)
    await r._pipni(1047, 100)
    asyncio.create_task(blikej(r))
    await hlidej_tlacitko(aplikace)


asyncio.run(hlavni())
