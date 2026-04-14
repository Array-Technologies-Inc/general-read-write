import os
import sys
import pandas as pd
from collections import defaultdict
import glob
import re
import time
import pickle
import socket
import struct
from time import sleep
from typing import List, Dict
from datetime import datetime
from queue import Empty, Queue

from common import common
from common.init_file import InitFile
from common.firmware import Firmware
from mac.mac_updater import read_site_macs, read_gateway_files, create_mac_files
from device.gateway import Gateway
from reporting.reporting import Reporting

from datetime import datetime, timezone, timedelta

from common.logger import TimedRotatingFileHandler

app_header = """    _                             ___ _____ ___   _  _         _              _
   /_\\  _ _ _ _ __ _ _  _   ___  / __|_   _|_ _| | \\| |___ _ _| |__ _ _ _  __| |
  / _ \\| '_| '_/ _` | || | |___| \\__ \\ | |  | |  | .` / _ \\ '_| / _` | ' \\/ _` |
 /_/ \\_\\_| |_| \\__,_|\\_, |       |___/ |_| |___| |_|\\_\\___/_| |_\\__,_|_||_\\__,_|
                     |__/                                                       """

# Dictionary for the gateways, the key is the IP and each value is a list of the devices of that gw
gateway_dict = defaultdict(type[Gateway])

class Table():
    def __init__(self, file_name, table_name):
        self.file_name = file_name
        self.table_name = table_name
        self.name = []
        self.id = []
        self.gw = []
        self.snc = []
        self.type = []
        self.product_id_init = []
        self.product_id_end = []
        self.connected = []
        self.percentage = []
        self.checksum_sent = []
        self.checksum_recv = []
        self.bootloader = []
        self.ended = []
        self.read_errors = []
        self.send_errors = []
        self.tsc_local_date = []
        self.tsc_utc_date = []
        self.duration = []
        self.read_requests = {}
        self.write_requests = {}

def get_app_version(version: str = "VERSION") -> str:
    return '1.1.0'

def get_folder_path():
    if getattr(sys, 'frozen', False):  # Si está ejecutándose como .exe
        return os.path.dirname(sys.executable)
    else:  # Si se ejecuta como script .py
        return os.path.dirname(__file__)

def read_config_map():
        #Read site config
        base_path = get_folder_path()
        config_path = os.path.join(base_path, "config")
        full_site_config_file = glob.glob(os.path.join(config_path, "Map*.xlsx"))
        if not full_site_config_file:
            print("There is not site config map file called 'Map___.xlsx'.\nThe program will exit in 10 seconds.")
            time.sleep(10)
            sys.exit()
        elif len(full_site_config_file) > 1:
            print("More than one site map file found, leave just one.\nThe program will exit in 10 seconds.")
            time.sleep(10)
            sys.exit()
        else:
            try:
                filename = os.path.basename(full_site_config_file[0])
                print(f"{filename} found.")
                match = re.search(r"Map[a]?_(.*?)_", filename)
                if not match:
                    match = re.search(r"Map[a]?_(.*?)\.xlsx", filename)
                if match:
                    site = match.group(1)
                else:
                    site = "Site_default"
                    print("Site name not valid, must be “Map_site name.xlsx”")
                given_config = pd.read_excel(full_site_config_file[0], sheet_name=None)
                try:
                    # Choose sheet
                    devices_config = given_config["Devices"]
                    device_table = Table(full_site_config_file[0], given_config)
                except Exception as e:
                    print(f"File cannot be opened: {e}")

                try:
                    # Choose columns
                    device_table.name = devices_config["TCU"]
                    device_table.id = devices_config["UnitId"]
                    device_table.gw = devices_config["GW"]
                    device_table.snc = devices_config["NCU"]
                    device_table.type = devices_config["Device Type"]
                    length = len(devices_config["TCU"])

                    try:
                        for col in devices_config.columns:
                            if "Read_" in col:
                                device_table.read_requests[col] = devices_config[col]
                                print(f" · Read register {col.replace("Read_", "")}")
                            if "Write_" in col:
                                device_table.write_requests[col] = devices_config[col]
                                print(f" · Write register {col.replace("Write_", "")}")

                        if not device_table.read_requests and not device_table.write_requests:
                            print(f"There is no read/write requests")
                    except Exception as e:
                        print(f"Cannot load the requests: {e}")

                    try:
                        device_table.product_id_init = devices_config["ProductId Init"]
                        device_table.product_id_sent = devices_config["ProductId Sent"]
                        device_table.product_id_end = devices_config["ProductId End"]
                        device_table.connected = devices_config["Connected"]
                        device_table.percentage = devices_config["Percentage"]
                        device_table.checksum_sent = devices_config["Checksum sent"]
                        device_table.checksum_recv = devices_config["Checksum recv"]
                        device_table.bootloader = devices_config["Bootloader"]
                        device_table.ended = devices_config["Ended"]
                        device_table.read_errors = devices_config["Read errors"]
                        device_table.send_errors = devices_config["Send errors"]
                        device_table.tsc_local_date = devices_config["TSC local date"]
                        device_table.tsc_utc_date = devices_config["TSC UTC date"]
                        device_table.duration = devices_config["Duration"]
                    except Exception as e:
                        print(f"Updating state cannot be charged: {e}")
                        device_table.product_id_init = ['0'] * length
                        device_table.product_id_sent = ['0'] * length
                        device_table.product_id_end = ['0'] * length
                        device_table.connected = ['No'] * length
                        device_table.percentage = [0] * length
                        device_table.checksum_sent = [0] * length
                        device_table.checksum_recv = [0] * length
                        device_table.bootloader = ['---'] * length
                        device_table.ended = ['---'] * length
                        device_table.read_errors = [0] * length
                        device_table.send_errors = [0] * length
                        device_table.tsc_local_date = [datetime.now().strftime("%d/%m/%Y - %H:%M:%S")] * length
                        device_table.tsc_utc_date = [datetime.now(timezone.utc).strftime("%d/%m/%Y - %H:%M:%S")] * length
                        device_table.duration = [timedelta()] * length

                    return full_site_config_file[0], devices_config, device_table, site

                except Exception as e:
                    print(f"Missing column: {e}")

            except Exception as e:
                print(f"Device sheet cannot be opened: {e}")



def create_gateways(config, device_table, tsc_frm_index, tsc_frm_list, iwc_frm_index, iwc_frm_list):
    for gw_ip in list(set(device_table.gw)):
        gateway_dict[gw_ip] = Gateway(
            gw_ip,
            config)

        if tsc_frm_list is not None and tsc_frm_index is not None:
            gateway_dict[gw_ip].add_new_tcs_version(tsc_frm_list[tsc_frm_index])

        if iwc_frm_list is not None and iwc_frm_index is not None:
            gateway_dict[gw_ip].add_new_iwc_version(iwc_frm_list[iwc_frm_index])

    for i, (name, id, gw_ip, snc, type, product_id_init, product_id_sent, product_id_end, connected, percentage,
         checksum_sent, checksum_recv, bootloader, ended, read_errors, send_errors, tsc_local_date, tsc_utc_date,
         duration) in \
        enumerate(
            zip(device_table.name, device_table.id, device_table.gw, device_table.snc, device_table.type,
                device_table.product_id_init, device_table.product_id_sent, device_table.product_id_end,
                device_table.connected, device_table.percentage, device_table.checksum_sent, device_table.checksum_recv,
                device_table.bootloader, device_table.ended, device_table.read_errors, device_table.send_errors,
                device_table.tsc_local_date, device_table.tsc_utc_date, device_table.duration)):
        read_req = {}
        write_req = {}
        for reg, value in device_table.read_requests.items():
            read_req[reg] = value[i]
        for reg, value in device_table.write_requests.items():
            write_req[reg] = value[i]
        if type == 'Controller':
            gateway_dict[gw_ip].add_tsc(name, id, snc, read_req, write_req, product_id_init, product_id_sent, product_id_end, connected, percentage, checksum_sent, checksum_recv, bootloader, ended, read_errors, send_errors, tsc_local_date, tsc_utc_date, duration)
        elif type == 'Meteo':
            gateway_dict[gw_ip].add_iwc(name, id, snc, read_req, write_req, product_id_init, product_id_sent, product_id_end, connected, percentage, checksum_sent, checksum_recv, bootloader, ended, read_errors, send_errors, tsc_local_date, tsc_utc_date, duration)
        else: 
            print(f"Device {name} has a non admited type: {type}")


def select_tsc_firmware(tsc_frm_list: List[Dict[str, str]]) -> str:
    frm_version = None
    if len(tsc_frm_list) > 1:
        print("Choose the TSC firmware you want to push:")
        i = 1
        for frm in tsc_frm_list:
            print("{}.- Install the version {} located in the file {}".format(
                i, frm["version"], frm["path"]))
            i += 1
        while frm_version is None:
            try:
                frm_version = int(input("Your choice: ")) - 1
                if frm_version >= i - 1 or frm_version < 0:
                    frm_version = None
                    raise ValueError
            except ValueError:
                print("Please enter a valid number.")

    elif len(tsc_frm_list) == 1:
        frm_version = 0
        print("There is the only version {} located in the file {}".format(
            tsc_frm_list[frm_version]["version"], tsc_frm_list[frm_version]["path"]
        ))
    else:
        print("Add a TSC firmware binary in the {} folder named 'imagen_vXX.bin'".format(
            common.FRIMWARE_DIR))
    return frm_version


def select_iwc_firmware(iwc_frm_list):
    frm_version = None
    if len(iwc_frm_list) > 1:
        print("Choose the IWC firmware you want to push:")
        i = 1
        for frm in iwc_frm_list:
            print("{}.- Install the version {} located in the file {}".format(
                i, frm["version"], frm["path"]))
            i += 1
        while frm_version is None:
            try:
                frm_version = int(input("Your choice: ")) - 1
                if frm_version >= i - 1 or frm_version < 0:
                    frm_version = None
                    raise ValueError
            except ValueError:
                print("Please enter a valid number.")
    elif len(iwc_frm_list) == 1:
        frm_version = 0
        print("There is the only version {} located in the file {}".format(
            iwc_frm_list[frm_version]["version"], iwc_frm_list[frm_version]["path"]
        ))
    else:
        print("Add a IWC firmware binary in the {} folder with named 'XXXXXX RSUXX Release.bin'".format(
            common.FRIMWARE_DIR))
    return frm_version


def main() -> None:

    print(app_header)

    app_version = get_app_version()

    print("You are using the fw updater version {}".format(app_version))
    print("Running update as principal.\n")

    firmware_dir = common.FRIMWARE_DIR
    frm = Firmware(firmware_dir)
    frm.load_frm_list()
    tsc_frm_list = frm.get_tsc_frm_list()
    iwc_frm_list = frm.get_iwc_frm_list()

    init_config = InitFile()
    print("Loading configuration file...")
    config = init_config.load()
    mac_files = int(config["init_FW"]["mac_files"])
    fw_update = int(config["init_FW"]["fw_update"])
    max_threads = int(config["init_FW"]["maximum_threads"])
    threads_per_gw = int(config["init_FW"]["threads_per_gateway"])
    loop_time = int(config["init_FW"]["loop_time"])

    if fw_update == 1:
        tsc_frm_version = None
        iwc_frm_version = None

        tsc_frm_index = select_tsc_firmware(tsc_frm_list)
        if tsc_frm_index is not None:
            tsc_frm_version = tsc_frm_list[tsc_frm_index]["version"]

        iwc_frm_index = select_iwc_firmware(iwc_frm_list)
        if iwc_frm_index is not None:
            iwc_frm_version = iwc_frm_list[iwc_frm_index]["version"]

    print("Loading devices...")
    devices_config_file, devices_config_table, devices_table, site = read_config_map()

    create_gateways(config, devices_table, tsc_frm_index, tsc_frm_list, iwc_frm_index, iwc_frm_list)

    if mac_files == 1:
        site_mac_dict = read_site_macs()
        individual_mac_dict = read_gateway_files()
        create_mac_files(gateway_dict, site_mac_dict, individual_mac_dict)

    if fw_update == 1:
        sum_tsc = 0
        sum_iwc = 0
        for gateway in gateway_dict.values():
            sum_tsc = sum_tsc + gateway.get_tsc_num()
            sum_iwc = sum_iwc + gateway.get_iwc_num()

        if sum_tsc > 0:
            print("You have selected these TSCs to read/write them:")
            for gateway in gateway_dict.values():
                tsc_list_string = ",".join(str(x) for x in gateway.get_tsc_keys())
                print("GW {}: {}".format(gateway.get_ip(), tsc_list_string))
            print("")

        else:
            print("You haven't selected any TSC.")

        time.sleep(3)

        if sum_iwc > 0:
            print("You have selected these IWCs to read/write them:")
            for gateway in gateway_dict.values():
                iwc_list_string = ",".join(str(x) for x in gateway.get_iwc_list())
                print("GW {}: {}".format(gateway.get_ip(), iwc_list_string))
            print("")
        else:
            print("You haven't selected any IWC.")

        time.sleep(3)

        report = Reporting(site, tsc_frm_version, iwc_frm_version)

        for gateway in gateway_dict.values():
            report.add_gateway(gateway)

        if tsc_frm_index is not None or iwc_frm_index is not None:
            is_alive = False
            threads_alive = 0
            for gateway in gateway_dict.values():
                if threads_alive <= max_threads - threads_per_gw: # Initiate threads no overpassing the limit
                    threads_alive += threads_per_gw
                    if gateway.get_tsc_num() > 0 or gateway.get_iwc_num() > 0:
                        gateway.start()
                        is_alive = True

            while is_alive:
                sleep(loop_time)
                is_alive = False
                threads_alive = 0
                for gateway in gateway_dict.values():
                    if gateway.is_alive():
                        is_alive = True
                        threads_alive += threads_per_gw # Count the max thread per gw, because they may be in creation
                    elif (threads_alive <= max_threads - threads_per_gw) and ((gateway.get_tsc_num() > (gateway.get_aborted_tsc() + gateway.get_full_tsc())) or (gateway.get_iwc_num() > (gateway.get_aborted_iwc() + gateway.get_full_iwc()))):
                        gateway.start()
                        is_alive = True
                        threads_alive += threads_per_gw
                devices_config_table = report.generate_report(devices_config_file, devices_config_table)


        report.set_end_time(datetime.now())
        report.generate_report(devices_config_file, devices_config_table)
    print("The process has finished.")
    sleep(10)


if __name__ == "__main__":
    main()
