import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import serial.tools.list_ports
import time
import os
import threading
from usb2can import USB2CAN  # Import knihovny usb2can pro komunikaci s USB2CAN


class FirmwareUploaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Firmware Uploader via USB2CAN")
        self.device = None  # USB2CAN zařízení

        # GUI prvky
        tk.Label(root, text="Vyberte CAN port:").grid(row=0, column=0, padx=10, pady=5)
        self.port_var = tk.StringVar()
        self.port_menu = ttk.Combobox(root, textvariable=self.port_var, values=self.get_serial_ports())
        self.port_menu.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(root, text="Rychlost (baud rate):").grid(row=1, column=0, padx=10, pady=5)
        self.baud_rate_var = tk.StringVar(value="500000")
        tk.Entry(root, textvariable=self.baud_rate_var).grid(row=1, column=1, padx=10, pady=5)

        tk.Label(root, text="Zadejte heslo (hex):").grid(row=2, column=0, padx=10, pady=5)
        self.password_var = tk.StringVar(value="CAFEBEEF")
        tk.Entry(root, textvariable=self.password_var).grid(row=2, column=1, padx=10, pady=5)

        self.file_path = ""
        tk.Button(root, text="Inicializovat zařízení", command=self.connect_device).grid(row=3, column=0, columnspan=2, pady=10)
        tk.Button(root, text="Vybrat soubor", command=self.select_file).grid(row=4, column=0, columnspan=2, pady=10)

        self.progress = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
        self.progress.grid(row=5, column=0, columnspan=2, pady=10)

        
        
        tk.Button(root, text="Odeslat firmware", command=self.start_send_firmware_thread).grid(row=6, column=0, columnspan=2, pady=10)
        tk.Button(root, text="Odpojit zařízení", command=self.disconnect_device).grid(row=8, column=0, columnspan=2, pady=10)

        self.status_label = tk.Label(root, text="Stav: Čekání na akci", fg="blue")
        self.status_label.grid(row=9, column=0, columnspan=2, pady=5)

    def update_status(self, text, color="blue"):
        self.status_label.config(text=f"Stav: {text}", fg=color)
        self.root.update_idletasks()

    def get_serial_ports(self):
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]

    def select_file(self):
        self.file_path = filedialog.askopenfilename(filetypes=[("Binární soubory", "*.bin"), ("Všechny soubory", "*.*")])
        if self.file_path:
            file_size = os.path.getsize(self.file_path)
            self.progress["maximum"] = file_size
            messagebox.showinfo("Vybrán soubor", f"Soubor: {self.file_path} ({file_size} bajtů)")

    def connect_device(self):
        try:
            port = self.port_var.get()
            baud_rate = int(self.baud_rate_var.get())
            self.device = USB2CAN(port, baud_rate)
            self.device.configure_usb2can()
            self.update_status("Připojeno k USB2CAN", "green")
        except Exception as e:
            messagebox.showerror("Chyba", f"Chyba připojení: {e}")

    def send_firmware(self):
        if not self.device:
            self.connect_device()

        if not self.device:
            return

        if not self.file_path:
            messagebox.showwarning("Chyba", "Vyberte soubor s firmwarem.")
            return

        try:
            # Odeslání hesla
            password = bytes.fromhex(self.password_var.get())
            endianess_hex = bytes.fromhex("FEEDFACE")
            self.update_status("Odesílám heslo...", "orange")
            self.device.send_can_message(0x11, list(endianess_hex + password))
            time.sleep(1)

            # Odeslání velikosti souboru
            file_size = os.path.getsize(self.file_path)
            size_data = file_size.to_bytes(8, byteorder='big')
            self.update_status("Odesílám velikost souboru...", "orange")
            self.device.send_can_message(0x12, list(size_data))
            time.sleep(1)

            # Odeslání dat
            self.update_status("Odesílám firmware...", "orange")
            bytes_sent = 0
            with open(self.file_path, "rb") as firmware_file:
                while chunk := firmware_file.read(8):
                    if len(chunk) < 8:
                        chunk += b'\xFF' * (8 - len(chunk))
                    self.device.send_can_message(0x13, list(chunk))
                    bytes_sent += len(chunk)
                    self.progress["value"] = bytes_sent
                    self.update_status(f"Odesláno {bytes_sent} / {file_size} bajtů", "orange")
                    time.sleep(0.01)

            self.update_status("Odesílání dokončeno", "green")
        except Exception as e:
            messagebox.showerror("Chyba", f"Chyba během přenosu: {e}")
        finally:
            self.disconnect_device()

    def start_send_firmware_thread(self):
        threading.Thread(target=self.send_firmware).start()

    def disconnect_device(self):
        if self.device:
            self.device.close()
            self.device = None
            self.update_status("Zařízení odpojeno", "blue")


# Hlavní běh aplikace
if __name__ == "__main__":
    root = tk.Tk()
    app = FirmwareUploaderApp(root)
    root.mainloop()
