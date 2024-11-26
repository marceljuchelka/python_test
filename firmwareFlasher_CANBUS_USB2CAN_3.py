# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from usb2can import USB2CAN, get_serial_ports  # Import knihovny
import os
import time

class FirmwareUploaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("USB2CAN Konfigurace a Ovládání")

        # Label a seznam sériových portů
        tk.Label(root, text="Vyberte COM port:").grid(row=0, column=0, padx=10, pady=5)
        self.port_var = tk.StringVar()
        self.port_menu = tk.OptionMenu(root, self.port_var, *get_serial_ports())
        self.port_menu.grid(row=0, column=1, padx=10, pady=5)

        # Nastavení parametrů sériového portu
        tk.Label(root, text="Rychlost (baud rate):").grid(row=1, column=0, padx=10, pady=5)
        self.baud_rate_var = tk.StringVar(value="115200")
        tk.Entry(root, textvariable=self.baud_rate_var).grid(row=1, column=1, padx=10, pady=5)

        # Tlačítko pro konfiguraci adaptéru
        self.configure_button = tk.Button(root, text="Konfigurovat adaptér", command=self.configure_adapter)
        self.configure_button.grid(row=2, column=0, columnspan=2, padx=10, pady=10)

        # Tlačítko pro výběr souboru s firmwarem
        self.select_file_button = tk.Button(root, text="Vyberte soubor s firmwarem", command=self.select_firmware_file)
        self.select_file_button.grid(row=3, column=0, columnspan=2, padx=10, pady=10)

        # Tlačítko pro flashování firmware
        self.flash_button = tk.Button(root, text="Flashovat firmware", command=self.flash_firmware)
        self.flash_button.grid(row=4, column=0, columnspan=2, padx=10, pady=10)

        # Tlačítko pro odpojení sériového portu
        self.disconnect_button = tk.Button(root, text="Odpojit adaptér", command=self.disconnect_adapter)
        self.disconnect_button.grid(row=5, column=0, columnspan=2, padx=10, pady=10)

        # Stavové štítky
        self.status_label = tk.Label(root, text="Stav: Čekání na akci", fg="blue")
        self.status_label.grid(row=6, column=0, columnspan=2, padx=10, pady=5)

        self.usb2can = None
        self.firmware_file_path = None

    def update_status(self, text, color="blue"):
        self.status_label.config(text=f"Stav: {text}", fg=color)
        self.root.update_idletasks()

    def configure_adapter(self):
        port = self.port_var.get()
        baud_rate = self.baud_rate_var.get()
        print(f"Konfiguruji adaptér na portu: {port}, s rychlostí: {baud_rate}")
        
        if not port:
            messagebox.showwarning("Chyba", "Vyberte COM port.")
            return

        try:
            baud_rate = int(baud_rate)
        except ValueError:
            messagebox.showerror("Chyba", "Neplatné nastavení baud rate.")
            return

        try:
            self.usb2can = USB2CAN(port, baud_rate)
            self.usb2can.configure_usb2can()
            self.update_status("Adaptér nakonfigurován", "green")
        except Exception as e:
            self.update_status(f"Chyba při konfiguraci: {e}", "red")

    def select_firmware_file(self):
        self.firmware_file_path = filedialog.askopenfilename(filetypes=[("Binární soubory", "*.bin")])
        if self.firmware_file_path:
            self.update_status(f"Vybraný soubor: {os.path.basename(self.firmware_file_path)}", "green")
        else:
            self.update_status("Žádný soubor nebyl vybrán", "red")

    def flash_firmware(self):
        if not self.usb2can:
            messagebox.showwarning("Chyba", "Adaptér není nakonfigurován.")
            return

        if not self.firmware_file_path:
            messagebox.showwarning("Chyba", "Žádný soubor s firmwarem nebyl vybrán.")
            return

        try:
            # Odeslat heslo pro inicializaci komunikace
            self.usb2can.send_can_message(0x11, [0xFE, 0xED, 0xFA, 0xCE, 0xCA, 0xFE, 0xBE, 0xEF])  # Heslo pro endianitu
            time.sleep(0.1)

            # Přečíst odpověď od bootloaderu
            response = self.usb2can.read_can_message()
            if response:
                self.update_status("Bootloader potvrzen, začínám flashování", "green")
            else:
                self.update_status("Chyba: Bootloader nepotvrdil přijetí hesla", "red")
                return

            with open(self.firmware_file_path, "rb") as firmware_file:
                data = firmware_file.read()
                # Rozdělit data na části, které lze poslat přes CAN (max 8 bajtů na zprávu)
                for i in range(0, len(data), 8):
                    chunk = data[i:i+8]
                    self.usb2can.send_can_message(0x11, list(chunk))
                    time.sleep(0.01)  # Krátká pauza mezi zprávami
                self.update_status("Firmware úspěšně nahrán", "green")
        except Exception as e:
            self.update_status(f"Chyba při flashování: {e}", "red")

    def disconnect_adapter(self):
        if self.usb2can:
            try:
                self.usb2can.close()
                self.update_status("Adaptér odpojen", "blue")
                self.usb2can = None
            except Exception as e:
                self.update_status(f"Chyba při odpojování: {e}", "red")

# Hlavní běh aplikace
if __name__ == "__main__":
    root = tk.Tk()
    app = FirmwareUploaderApp(root)
    root.mainloop()
