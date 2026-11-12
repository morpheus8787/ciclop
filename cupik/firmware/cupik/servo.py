# Cupík – ovládání serv SG90

STRED_US = 1500           # impuls pro střední polohu
US_NA_STUPEN = 1000 / 90  # SG90: 500–2500 µs ≈ 0–180°
MIN_US = 600              # bezpečné meze, ať servo nenaráží na doraz
MAX_US = 2400
FREKVENCE = 50


def uhel_na_us(uhel, trim=0, smer=1):
    """Převede úhel kloubu (°) na délku impulsu v µs.

    smer (+1/-1) otočí směr serva, trim (°) opraví nepřesné nasazení páky.
    """
    us = STRED_US + (smer * uhel + trim) * US_NA_STUPEN
    return int(max(MIN_US, min(MAX_US, us)))


class Servo:
    def __init__(self, pin, trim=0, smer=1):
        import machine
        self._pwm = machine.PWM(machine.Pin(pin), freq=FREKVENCE)
        self.trim = trim
        self.smer = smer

    def nastav(self, uhel):
        self._pwm.duty_ns(uhel_na_us(uhel, self.trim, self.smer) * 1000)

    def uvolni(self):
        """Přestane servo držet (šetří baterie)."""
        self._pwm.duty_ns(0)
