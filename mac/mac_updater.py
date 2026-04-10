import os
import sys
import pandas as pd
from collections import defaultdict
import glob
import re
import time

def get_mac_folder_path():
    if getattr(sys, 'frozen', False):  # Si está ejecutándose como .exe
        base_path = os.path.dirname(sys.executable)
        return os.path.join(base_path, "mac")
    else:  # Si se ejecuta como script .py
        return os.path.dirname(__file__)

def read_site_macs():
    mac_folder = get_mac_folder_path()
    full_site_mac_file = glob.glob(os.path.join(mac_folder, "Device list*.xlsx"))
    if not full_site_mac_file:
        print("There is not site config map file called 'Device list___.xlsx'.")
        time.sleep(3)
    elif len(full_site_mac_file) > 1:
        print("More than one site MAC file found, leave just one.")
        time.sleep(3)
    else:
        try:
            filename = os.path.basename(full_site_mac_file[0])
            print(f"{filename} found.")
            # Read files to dictionaries where the sheets names are the keys
            given_macs = pd.read_excel(full_site_mac_file[0], engine="openpyxl")
            try:
                # Take columns
                devices_name_mac = given_macs["Name"]
                devices_mac = given_macs["Device ZM/Mac Address"]
                mac_dict = defaultdict(lambda: "")
                for name, mac in zip(devices_name_mac, devices_mac):
                    mac_dict[name] = mac
                return mac_dict
            except Exception as e:
                print(f"Missing column: {e}")

        except Exception as e:
            print(f"Device sheet cannot be opened: {e}")


def read_gateway_files():
    mac_folder = get_mac_folder_path()
    gateway_files = glob.glob(os.path.join(mac_folder, "Mac list SNC_*-*.txt"))
    if not gateway_files:
        print("There are not individual Mac list files.")
    else:
        try:
            gw_dict = defaultdict(lambda: defaultdict(lambda: ""))
            for file in gateway_files:
                try:
                    # Extraer la información entre "SNC_" y ".txt"
                    match = re.search(r"SNC_(.+)-(.+)\.txt", file)
                    if match:
                        snc, gw_ip = match.groups()
                        print(f"File: {file} -> SNC: {snc}, GW: {gw_ip}")
                        # Leer y mostrar el contenido del archivo
                        try:
                            with open(file, "r", encoding="utf-8") as f:
                                for line in f:
                                    id, mac = line.strip().split(";")
                                    gw_dict[gw_ip][id] = mac
                        except Exception as e:
                            print(f"File cannot be read: {e}")
                except Exception as e:
                    print(f"File has a wrong name: {e}")
            return gw_dict
        except Exception as e:
            print(f"GW Mac list cannot be found: {e}")


def create_mac_files(gateway_dict, site_mac_dict, individual_mac_dict):
    mac_folder = get_mac_folder_path()
    for gateway in gateway_dict.values():
        mac_list_text = []
        # mac_list_pickle = {}
        try:
            gw_folder_path = os.path.join(mac_folder, str(gateway.get_ip()))
            file_path = os.path.join(gw_folder_path, "MAC_List.txt")
            os.makedirs(gw_folder_path, exist_ok=True)

            for tsc in gateway.get_tsc_list().values():
                try:
                    mac = site_mac_dict[tsc.name]
                except:
                    mac = "nan"
                if individual_mac_dict is not None:
                    if individual_mac_dict[gateway.get_ip()]:
                        mac = individual_mac_dict[gateway.get_ip()][str(tsc.get_id())]
                tsc.set_mac(mac)
                if len(str(tsc.mac)) < 4:  # The value is nan if it is not assigned
                    mac_list_text.append(str(tsc.get_id()) + ";\n")
                    # mac_list_pickle[tsc.get_id()] = ""
                else:
                    mac_list_text.append(str(tsc.get_id()) + ";" + str(tsc.get_mac()) + "\n")
                    # mac_list_pickle[tsc.get_id()] = str(tsc.get_mac())

            for iwc in gateway.get_iwc_list().values():
                try:
                    mac = site_mac_dict[iwc.name]
                except:
                    mac = "nan"
                if individual_mac_dict is not None:
                    if individual_mac_dict[gateway.get_ip()]:
                        mac = individual_mac_dict[gateway.get_ip()][str(iwc.get_id())]
                iwc.set_mac(mac)
                if len(str(iwc.mac)) < 4:  # The value is nan if it is not assigned
                    mac_list_text.append(str(iwc.get_id()) + ";\n")
                    # mac_list_pickle[tsc.get_id()] = ""
                else:
                    mac_list_text.append(str(iwc.get_id()) + ";" + str(iwc.get_mac()) + "\n")
                    # mac_list_pickle[tsc.get_id()] = str(tsc.get_mac())
            with open(file_path, "w", encoding="utf-8") as mac_file:
                mac_file.write("".join(mac_list_text))

            # with open(f"mac/MAC_List_{gateway.ip}.pkl", "wb") as mac_file:
            #    pickle.dump(mac_list_pickle, mac_file)

        except Exception as e:
            print(f"GW {gateway.get_ip()} cannot creat mac file: {e}")

        # try:
        #     data_configured = pickle.dumps(mac_list_pickle, protocol=2)
        #     data_len_packed = struct.pack('>I', len(data_configured))
        #     with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        #         client_socket.connect((gateway.get_ip(), 502))  # Conectar con el servidor
        #         client_socket.sendall(data_len_packed)
        #         client_socket.sendall(data_configured)

        #         confirmation_bytes = client_socket.recv(1024)
        #         confirmation = confirmation_bytes.decode('utf-8', errors='ignore')
        #         if confirmation:
        #             gateway.set_mac_file_updated(True)
        #             print(f"GW {gateway.get_ip()} response: {confirmation}")
        #         else:
        #             print(f"GW {gateway.get_ip()} response: No response")
        #             time.sleep(5)
        # except Exception as e:
        #     print(f"GW {gateway.get_ip()} response: {e}")

                
