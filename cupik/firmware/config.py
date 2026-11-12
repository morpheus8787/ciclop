# Cupík – zapojení a Wi-Fi (ESP32-C3 SuperMini)

# Serva: kyčel L, kyčel P, kotník L, kotník P
PINY_SERV = (3, 4, 5, 6)
PIN_REZERVA = 7          # 5. servo (ruka, ocas…) – zatím nevyužito
PIN_BZUCAK = 10          # pasivní piezo bzučák
PIN_TRIG = 0             # HC-SR04 TRIG
PIN_ECHO = 1             # HC-SR04 ECHO (přes dělič 1k/2k!)
PIN_TLACITKO = 9         # tlačítko BOOT na desce = spustí uložený program
PIN_LED = 8              # modrá LED na desce (svítí v nule)

# Wi-Fi: robot si vytvoří vlastní síť „Cupik-XXXX“.
# Heslo napište na štítek na robota. Musí mít aspoň 8 znaků.
WIFI_HESLO = "cupik123"
