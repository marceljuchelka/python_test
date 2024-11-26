#knihovna pro usb2can

# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import serial
import time

class USB2CAN:
    def __init__(self, port, baudrate=115200):
        self.ser = serial.Serial(port, baudrate, timeout=1)
        self.START_BYTE = 0x0F

    def send_command(self, command, data=[]):
        """
        Odešle příkaz na USB2CAN adaptér.
        """
        length = len(data)  # Upraveno: Správná délka datové části zprávy
        message = [self.START_BYTE, command, length] + data
        self.ser.write(bytearray(message))
        print(f"Odesílám: {bytearray(message).hex()}")  # Přidán výpis odeslaných dat
        time.sleep(0.1)
        response = self.ser.read(self.ser.in_waiting)
        print(f"Odpověď ze send_command: {response.hex()}")
        return response

    def configure_usb2can(self):
        """
        Inicializace adaptéru USB2CAN do normálního režimu.
        """
        try:
            # 1. Nastavit konfigurační mód
            self.send_command(2)  # CONFIG_MODE

            # 2. Reset mód
            self.send_command(18, [0x00, 0x01])  # WRITE_REG: Mode register (address 0) = 0x01

            # 3. Nastavit Clock Divider
            self.send_command(18, [0x1C, 0xC0])  # WRITE_REG: Clock Divider (address 0x1C) = 0xC0

            # 4. Nastavit filtry (žádné filtrování)
            self.send_command(18, [0x04, 0x00])  # WRITE_REG: Acceptance Code (address 0x04) = 0x00
            self.send_command(18, [0x05, 0xFF])  # WRITE_REG: Acceptance Mask (address 0x05) = 0xFF

            # 5. Nastavit Output Control
            self.send_command(18, [0x1A, 0xDA])  # WRITE_REG: Output Control (address 0x1A) = 0xDA

            # 6. Nastavit Interrupt Enable
            self.send_command(18, [0x0C, 0x03])  # WRITE_REG: Interrupt Enable (address 0x0C) = 0x03

            # 7. Nastavit Bus Timing
            self.send_command(18, [0x06, 0x00])  # WRITE_REG: Bus Timing 0 (address 0x06) = 0x00
            self.send_command(18, [0x07, 0x1C])  # WRITE_REG: Bus Timing 1 (address 0x07) = 0x1C
            
            # 8. Nastavit parametry CMD_TRANSMIT_CRITICAL_LIMIT a CMD_TRANSMIT_READY_LIMIT
            self.send_command(32, [0x00, 18])  # CMD_TRANSMIT_CRITICAL_LIMIT = 18
            self.send_command(32, [0x01, 17])  # CMD_TRANSMIT_READY_LIMIT = 17

            # 9. Přepnout do normálního režimu
            self.send_command(3)  # NORMAL_MODE
            
            # 10. Nastavit režim registru Mode
            self.send_command(18, [0x00, 0x00])  # WRITE_REG: Mode register (address 0) = 0x00

            print("USB2CAN adaptér úšpěšně inicializován jako převodník.")
        except Exception as e:
            print(f"Chyba při konfiguraci: {e}")

    def send_can_message(self, can_id, data):
        """
        Odešle CAN zprávu.
        """
        try:
            dlc = len(data)  # Data Length Code (DLC)
            if dlc > 8:
                raise ValueError("Délka datového pole nemůže být větší než 8 bajtů.")
            
            # Sestavení CAN zprávy s identifikátorem a daty
            id_high = (can_id >> 3) & 0xFF  # Horní část identifikátoru (ID), 8 bitů
            id_low = (can_id & 0x07) << 5  # Dolních 3 bity identifikátoru, posunuty vlevo o 5 bitů
            frame_info = dlc  # Standardní rámec, délka datového pole (DLC)
            
            message = [frame_info, id_high, id_low] + data  # Frame info, Identifier, a data
            
            length = len(message)  # Správná délka zprávy (včetně frame_info)
            full_message = [self.START_BYTE, 0x40, length] + message  # Přidání START_BYTE a příkazu WRITE_MESSAGE
            
            self.ser.write(bytearray(full_message))
            print(f"Odesílám CAN zprávu: {bytearray(full_message).hex()}")  # Přidán výpis odeslané CAN zprávy
            print(f"CAN zpráva s ID {hex(can_id)} odeslána.")
            response = self.ser.read(self.ser.in_waiting)
            print(f"Odpověď po odeslání CAN zprávy: {response.hex()}")  # Přidán výpis přijaté odpovědi
        except Exception as e:
            print(f"Chyba při odesílání CAN zprávy: {e}")

    def read_can_message(self):
        """
        Přečte CAN zprávu z adaptéru pomocí příkazu READ_MESSAGE.
        """
        try:
            self.send_command(65)  # READ_MESSAGE command
            data = self.ser.read(self.ser.in_waiting)  # Číst všechna dostupná data
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
            self.send_command(18, [0x00, 0x01])  # WRITE_REG: Mode register (address 0) = 0x01 (reset mode)
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
    usb2can.send_can_message(0x11, [0xFE, 0xED, 0xFA, 0xCE, 0xCA, 0xFE, 0xBE, 0xEF])
    
    # Opakované načítání odpovědi
    for _ in range(10):
        response = usb2can.read_can_message()
        if response:
            print(f"Odpověď: {response.hex()}")
        time.sleep(0.001)  # Krátká pauza mezi pokusy o čtení
    
    usb2can.close()
