# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import serial
import time
import tkinter as tk
from tkinter import ttk, messagebox
import serial.tools.list_ports

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
        time.sleep(0.1)
        return self.ser.read(self.ser.in_waiting)

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

            print("USB2CAN adaptér úspěšně inicializován jako převodník.")
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
            time.sleep(0.1)
            print(f"CAN zpráva s ID {hex(can_id)} odeslána.")
        except Exception as e:
            print(f"Chyba při odesílání CAN zprávy: {e}")

    def read_can_message(self):
        """
        Přečte CAN zprávu z adaptéru.
        """
        try:
            self.send_command(65)  # READ_MESSAGE command
            data = self.ser.read(self.ser.in_waiting)
            if data:
                print(f"Přijatá CAN zpráva: {data.hex()}")
            else:
                print("Žádná CAN zpráva nebyla přijata.")
        except Exception as e:
            print(f"Chyba při čtení CAN zprávy: {e}")

    def close(self):
        """
        Uzavře sériové spojení.
        """
        self.ser.close()

# GUI pro konfiguraci USB2CAN
class FirmwareUploaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("USB2CAN Konfigurace a Ovládání")

        # Label a seznam sériových portů
        tk.Label(root, text="Vyberte COM port:").grid(row=0, column=0, padx=10, pady=5)
        self.port_var = tk.StringVar()
        self.port_menu = tk.OptionMenu(root, self.port_var, *self.get_serial_ports())
        self.port_menu.grid(row=0, column=1, padx=10, pady=5)

        # Nastavení parametrů sériového portu
        tk.Label(root, text="Rychlost (baud rate):").grid(row=1, column=0, padx=10, pady=5)
        self.baud_rate_var = tk.StringVar(value="115200")
        tk.Entry(root, textvariable=self.baud_rate_var).grid(row=1, column=1, padx=10, pady=5)

        # Tlačítko pro konfiguraci adaptéru
        self.configure_button = tk.Button(root, text="Konfigurovat adaptér", command=self.configure_adapter)
        self.configure_button.grid(row=2, column=0, columnspan=2, padx=10, pady=10)

        # Tlačítko pro odeslání CAN zprávy
        self.send_button = tk.Button(root, text="Odeslat CAN zprávu", command=self.send_can_message)
        self.send_button.grid(row=3, column=0, columnspan=2, padx=10, pady=10)

        # Tlačítko pro čtení CAN zprávy
        self.read_button = tk.Button(root, text="Přečíst CAN zprávu", command=self.read_can_message)
        self.read_button.grid(row=4, column=0, columnspan=2, padx=10, pady=10)

        # Tlačítko pro odpojení sériového portu
        self.disconnect_button = tk.Button(root, text="Odpojit adaptér", command=self.disconnect_adapter)
        self.disconnect_button.grid(row=5, column=0, columnspan=2, padx=10, pady=10)

        # Stavové štítky
        self.status_label = tk.Label(root, text="Stav: Čekání na akci", fg="blue")
        self.status_label.grid(row=6, column=0, columnspan=2, padx=10, pady=5)

        self.usb2can = None

    def update_status(self, text, color="blue"):
        self.status_label.config(text=f"Stav: {text}", fg=color)
        self.root.update_idletasks()

    def get_serial_ports(self):
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]

    def configure_adapter(self):
        port = self.port_var.get()
        baud_rate = self.baud_rate_var.get()
        print(f"Konfiguruji adaptér na portu: {port}, s rychlostí: {baud_rate}")
        port = self.port_var.get()
        if not port:
            messagebox.showwarning("Chyba", "Vyberte COM port.")
            return

        try:
            baud_rate = int(self.baud_rate_var.get())
        except ValueError:
            messagebox.showerror("Chyba", "Neplatné nastavení baud rate.")
            return

        try:
            self.usb2can = USB2CAN(port, baud_rate)
            self.usb2can.configure_usb2can()
            self.update_status("Adaptér nakonfigurován", "green")
        except Exception as e:
            self.update_status(f"Chyba při konfiguraci: {e}", "red")

    def send_can_message(self):
        if not self.usb2can:
            messagebox.showwarning("Chyba", "Adaptér není nakonfigurován.")
            return

        try:
            self.usb2can.send_can_message(0x12, [0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28])
            self.update_status("CAN zpráva odeslána", "green")
        except Exception as e:
            self.update_status(f"Chyba při odesílání CAN zprávy: {e}", "red")

    def read_can_message(self):
        if not self.usb2can:
            messagebox.showwarning("Chyba", "Adaptér není nakonfigurován.")
            return

        try:
            self.usb2can.read_can_message()
            self.update_status("CAN zpráva přečtena", "green")
        except Exception as e:
            self.update_status(f"Chyba při čtení CAN zprávy: {e}", "red")

    def disconnect_adapter(self):
        if self.usb2can:
            try:
                self.usb2can.close()
                self.update_status("Adaptér odpojen", "blue")
                self.usb2can = None
            except Exception as e:
                self.update_status(f"Chyba při odpojování: {e}", "red")

# Hlavní běh aplikace
root = tk.Tk()
app = FirmwareUploaderApp(root)
root.mainloop()
