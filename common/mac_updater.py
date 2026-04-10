import pandas as pd
from collections import defaultdict
import glob
import re
import sys
import time

#Register all the devices
devices = {}

# Dictionary for the gateways, the key is the IP and each value is a list of the devices of that gw
gateway_devices = defaultdict(list)

class Device():
    def __init__(self, name, id, gw, snc, type):
        self.name = name
        self.id = id
        self.gw = gw
        self.snc = snc
        self.type = type
    def __str__(self):
        return f"{self.name} with id={self.id} belongs to gw={self.gw}"
    def add_mac(self, mac=""):
        self.mac = mac

class Mac():

    # Asig value test
    # devices_config.loc[devices_config["TCU"] == device.name, "Listed"] = "Yes"

    def read_gateway_files():
        print("The program will check individual Mac list files in few seconds...")
        time.sleep(5)
        # Buscar archivos que coincidan con el patrón
        gateway_files = glob.glob("Mac list SNC_*-*.txt")

        # Verificar si se encontraron archivos
        if not gateway_files:
            print("There are not individual Mac list files.\nThe program will close in few seconds...")
            sys.exit()
        else:
            for file in gateway_files:
                # Extraer la información entre "SNC_" y ".txt"
                match = re.search(r"SNC_(.+)-(.+)\.txt", file)
                if match:
                    snc, gw = match.groups()
                    print(f"File: {file} -> SNC: {snc}, GW: {gw}")

                    # Leer y mostrar el contenido del archivo
                    with open(file, "r", encoding="utf-8") as f:
                        data = f.read()
                        #print("\nFile data:\n")
                        #print(data)
                        #print("="*50)  # Separador entre archivos

    def read_config_map():
        #Read site config
        full_site_config_file = glob.glob("Map*.xlsx")
        if not full_site_config_file:
            print("There is not site config map file called 'Map___.xlsx'.")
        elif len(full_site_config_file) > 1:
            print("More than one site map file found, leave just one.")
        else:
            try:
                print(f"{full_site_config_file[0]} found.")
                given_config = pd.read_excel(full_site_config_file[0], sheet_name=None)
                try:
                    # Choose sheet
                    devices_config = given_config["Devices"]
                except Exception as e:
                    print(f"File cannot be opened: {e}")

                try:
                    # Choose columns
                    devices_name = devices_config["TCU"]
                    devices_id = devices_config["UnitId"]
                    devices_gw = devices_config["GW"]
                    devices_snc = devices_config["NCU"]
                    devices_type = devices_config["Device Type"]  

                    for name, id, gw, snc, type in zip(devices_name, devices_id, devices_gw, devices_snc, devices_type):
                        devices[name] = Device(name, id, gw, snc, type)
                        gateway_devices[devices[name].gw].append(devices[name]) # Add the device to the list of the dictionary of gateways
                    
                    return full_site_config_file[0], devices_config

                except Exception as e:
                    print(f"Missing column: {e}")

            except Exception as e:
                print(f"Device sheet cannot be opened: {e}")
        
    def read_site_macs():
        full_site_mac_file = glob.glob("Device list*.xlsx")
        if not full_site_mac_file:
            print("There is not site config map file called 'Device list___.xlsx'.")
        elif len(full_site_mac_file) > 1:
            print("More than one site MAC file found, leave just one.")
        else:
            print(f"{full_site_mac_file[0]} found.")
            # Read files to dictionaries where the sheets names are the keys
            given_macs = pd.read_excel(full_site_mac_file[0], engine="openpyxl")

            # Take columns
            devices_name_mac = given_macs["Name"]
            devices_mac = given_macs["Device ZM/Mac Address"]

            # Link the mac with the devices
            for name, mac in zip(devices_name_mac, devices_mac):
                try:
                    devices[name].add_mac(mac)
                except Exception as e:
                    print(f"There is not a device with name {name}: {e}")

    def generate_mac_list():
            # Collect the id and mac of the devices of each GW
            for gw_ip, gw_devices in gateway_devices.items():
                mac_list_text = []
                print(f"Generating MAC_List.txt for GW: {gw_ip}")
                for device in gw_devices:
                    if len(str(device.mac)) < 4: # The value is nan if it is not assigned
                        mac_list_text.append(str(device.id) + ";\n")
                    else:
                        mac_list_text.append(str(device.id) + ";" + str(device.mac) + "\n")
                #print("".join(mac_list_text))
                with open("MAC_List.txt", "w") as mac_file:
                    mac_file.write("".join(mac_list_text))

    def save_data(excel_file, sheet_data):
        # Save the excel sheet
        with pd.ExcelWriter(excel_file, engine="openpyxl", mode="w") as writer:
            sheet_data.to_excel(writer, sheet_name="Devices", index=False)

                
