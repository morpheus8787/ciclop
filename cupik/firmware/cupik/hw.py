# Cupík – hardware (jen MicroPython na ESP32-C3)

import machine
import time
import config
from cupik.servo import Servo


def serva():
    return [Servo(pin) for pin in config.PINY_SERV]


class Bzucak:
    def __init__(self, pin=config.PIN_BZUCAK):
        self._pwm = machine.PWM(machine.Pin(pin), freq=1000, duty_u16=0)

    def ton(self, frekvence):
        self._pwm.freq(int(frekvence))
        self._pwm.duty_u16(32768)

    def ticho(self):
        self._pwm.duty_u16(0)


class Dalkomer:
    """Ultrazvukový senzor HC-SR04."""
    MAX_US = 25000  # ~4 m

    def __init__(self, trig=config.PIN_TRIG, echo=config.PIN_ECHO):
        self._trig = machine.Pin(trig, machine.Pin.OUT, value=0)
        self._echo = machine.Pin(echo, machine.Pin.IN)

    def cm(self):
        self._trig.value(0)
        time.sleep_us(5)
        self._trig.value(1)
        time.sleep_us(10)
        self._trig.value(0)
        us = machine.time_pulse_us(self._echo, 1, self.MAX_US)
        if us < 0:
            return -1
        return round(us / 58)
