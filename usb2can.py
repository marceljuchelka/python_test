# knihovna pro usb2can bez verbose */

# -*- coding: utf-8 -*-
import sys
import serial
import time
sys.stdout.reconfigure(encoding='utf-8')


class USB2CAN:
    def __init__(self, port, baudrate=115200):  # self musí být první argument
        self.ser = serial.Serial(port, baudrate, timeout=1)
        self.START_BYTE = 0x0F

    def send_command(self, command, data=[]):
        """
        Odešle příkaz na USB2CAN adaptér.
        """
        length = len(data)  # Upraveno: Správná délka datové části zprávy
        message = [self.START_BYTE, command, length] + data
        self.ser.write(bytearray(message))
        # Přidán výpis odeslaných dat
        print(f"Odesílám: {bytearray(message).hex()}")
        time.sleep(0.1)

    def configure_usb2can(self):
        """
        Inicializace adaptéru USB2CAN do normálního režimu.
        """
        try:
            # 1. Nastavit konfigurační mód
            self.send_command(2)  # CONFIG_MODE
            time.sleep(0.1)
            response = self.ser.read(self.ser.in_waiting)
            print(f"Odpověď ze send_command: {response.hex()}")

            # 2. Reset mód
            # WRITE_REG: Mode register (address 0) = 0x01
            self.send_command(18, [0x00, 0x01])
            response = self.ser.read(self.ser.in_waiting)
            print(f"Odpověď ze send_command: {response.hex()}")

            # 3. Nastavit Clock Divider
            # WRITE_REG: Clock Divider (address 0x1C) = 0xC0
            self.send_command(18, [0x1C, 0xC0])
            response = self.ser.read(self.ser.in_waiting)
            print(f"Odpověď ze send_command: {response.hex()}")

            # 4. Nastavit filtry (žádné filtrování)
            # WRITE_REG: Acceptance Code (address 0x04) = 0x00
            self.send_command(18, [0x04, 0x00])
            response = self.ser.read(self.ser.in_waiting)
            print(f"Odpověď ze send_command: {response.hex()}")

            # WRITE_REG: Acceptance Mask (address 0x05) = 0xFF
            self.send_command(18, [0x05, 0xFF])
            response = self.ser.read(self.ser.in_waiting)
            print(f"Odpověď ze send_command: {response.hex()}")

            # 5. Nastavit Output Control
            # WRITE_REG: Output Control (address 0x1A) = 0xDA
            self.send_command(18, [0x1A, 0xDA])
            response = self.ser.read(self.ser.in_waiting)
            print(f"Odpověď ze send_command: {response.hex()}")

            # 6. Nastavit Interrupt Enable
            # WRITE_REG: Interrupt Enable (address 0x0C) = 0x03
            self.send_command(18, [0x0C, 0x03])
            response = self.ser.read(self.ser.in_waiting)
            print(f"Odpověď ze send_command: {response.hex()}")

            # 7. Nastavit Bus Timing
            # WRITE_REG: Bus Timing 0 (address 0x06) = 0x00
            self.send_command(18, [0x06, 0x00])
            response = self.ser.read(self.ser.in_waiting)
            print(f"Odpověď ze send_command: {response.hex()}")
            # WRITE_REG: Bus Timing 1 (address 0x07) = 0x1C
            self.send_command(18, [0x07, 0x1C])
            response = self.ser.read(self.ser.in_waiting)
            print(f"Odpověď ze send_command: {response.hex()}")

            # 8. Nastavit parametry CMD_TRANSMIT_CRITICAL_LIMIT a CMD_TRANSMIT_READY_LIMIT
            # CMD_TRANSMIT_CRITICAL_LIMIT = 18
            self.send_command(32, [0x00, 18])
            response = self.ser.read(self.ser.in_waiting)
            print(f"Odpověď ze send_command: {response.hex()}")
            self.send_command(32, [0x01, 17])  # CMD_TRANSMIT_READY_LIMIT = 17
            response = self.ser.read(self.ser.in_waiting)
            print(f"Odpověď ze send_command: {response.hex()}")

            # 9. Přepnout do normálního režimu
            self.send_command(3)  # NORMAL_MODE
            response = self.ser.read(self.ser.in_waiting)
            print(f"Odpověď ze send_command: {response.hex()}")

            # 10. Nastavit režim registru Mode
            # WRITE_REG: Mode register (address 0) = 0x00
            self.send_command(18, [0x00, 0x00])
            response = self.ser.read(self.ser.in_waiting)
            print(f"Odpověď ze send_command: {response.hex()}")

            print("USB2CAN adaptér úšpěšně inicializován jako převodník.")
        except Exception as e:
            print(f"Chyba při konfiguraci: {e}")
            response = self.ser.read(self.ser.in_waiting)
            print(f"Odpověď ze send_command: {response.hex()}")

    def send_can_message(self, can_id, data):
        """
        Odešle CAN zprávu.
        """
        try:
            dlc = len(data)  # Data Length Code (DLC)
            if dlc > 8:
                raise ValueError(
                    "Délka datového pole nemůže být větší než 8 bajtů.")

            # Sestavení CAN zprávy s identifikátorem a daty
            # Horní část identifikátoru (ID), 8 bitů
            id_high = (can_id >> 3) & 0xFF
            # Dolních 3 bity identifikátoru, posunuty vlevo o 5 bitů
            id_low = (can_id & 0x07) << 5
            frame_info = dlc  # Standardní rámec, délka datového pole (DLC)

            message = [frame_info, id_high, id_low] + \
                data  # Frame info, Identifier, a data

            length = len(message)  # Správná délka zprávy (včetně frame_info)
            # Přidání START_BYTE a příkazu WRITE_MESSAGE
            full_message = [self.START_BYTE, 0x40, length] + message

            self.ser.write(bytearray(full_message))
            # Přidán výpis odeslané CAN zprávy
            print(f"Odesílám CAN zprávu: {bytearray(full_message).hex()}")
            print(f"CAN zpráva s ID {hex(can_id)} odeslána.")
            response = self.ser.read(self.ser.in_waiting)
            # Přidán výpis přijaté odpovědi
            print(f"Odpověď po odeslání CAN zprávy: {response.hex()}")
        except Exception as e:
            print(f"Chyba při odesílání CAN zprávy: {e}")

    def read_can_message(self):
        """
        Přečte CAN zprávu z adaptéru pomocí příkazu READ_MESSAGE.
        """
        try:
            self.send_command(65)  # READ_MESSAGE command
            # Číst všechna dostupná data
            data = self.ser.read(self.ser.in_waiting)
            if data:
                print(f"Přijatá CAN zpráva: {data.hex()}")
                return data
            else:
                print("Žádná CAN zpráva nebyla přijata.")
        except Exception as e:
            print(f"Chyba při čtení CAN zprávy: {e}")
        return None

    def reset_usb2can(self):
        """
        Resetuje USB2CAN adaptér.
        """
        try:
            # Přepnout do konfiguračního módu
            self.send_command(2)  # CONFIG_MODE
            self.send_command(1)  # BOOT_MODE
            # Resetovat adaptér
            # WRITE_REG: Mode register (address 0) = 0x01 (reset mode)
            self.send_command(18, [0x00, 0x01])
            print("Adaptér byl resetován.")
        except Exception as e:
            print(f"Chyba při resetování adaptéru: {e}")

    def close(self):
        """
        Uzavře sériové spojení.
        """
        self.reset_usb2can()  # Reset před odpojením
        if self.ser and self.ser.is_open:
            self.ser.close()

# Funkce pro získání seznamu sériových portů


def get_serial_ports():
    import serial.tools.list_ports
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]


# Příklad použití knihovny
if __name__ == "__main__":
    port = "COM5"
    baud_rate = 500000  # Zvýšená rychlost
    usb2can = USB2CAN(port, baud_rate)
    usb2can.configure_usb2can()

    # Odeslat kombinované heslo
    usb2can.send_can_message(
        0x11, [0xFE, 0xED, 0xFA, 0xCE, 0xCA, 0xFE, 0xBE, 0xEF])

    # Opakované načítání odpovědi
    for _ in range(10):
        response = usb2can.read_can_message()
        if response:
            print(f"Odpověď: {response.hex()}")
        time.sleep(0.001)  # Krátká pauza mezi pokusy o čtení

    usb2can.close()
