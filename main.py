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
        self.read_requests = {}
        self.write_requests = {}
        self.mask_write_requests = {}

def get_app_version(version: str = "VERSION") -> str:
    return '1.0.0'

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
                            if "Read" in col:
                                device_table.read_requests[col] = devices_config[col]
                                print(f" · {col}")
                            if "Write" in col:
                                device_table.write_requests[col] = devices_config[col]
                                print(f" · {col}")
                            if "Mask_" in col:
                                device_table.mask_write_requests[col] = devices_config[col]
                                print(f" · Write with mask register {col.replace("Mask_", "")}")

                        if not device_table.read_requests and not device_table.write_requests and not device_table.mask_write_requests:
                            print(f"There is no read/write requests")
                    except Exception as e:
                        print(f"Cannot load the requests: {e}")

                    return full_site_config_file[0], devices_config, device_table, site

                except Exception as e:
                    print(f"Missing column: {e}")

            except Exception as e:
                print(f"Device sheet cannot be opened: {e}")



def create_gateways(config, device_table, tsc_enable: bool, iwc_enable: bool):
    for gw_ip in list(set(device_table.gw)):
        gateway_dict[gw_ip] = Gateway(
            gw_ip,
            config)

    for i, (name, id, gw_ip, snc, type) in enumerate(zip(device_table.name, device_table.id, device_table.gw, device_table.snc, device_table.type)):
        read_req = {}
        write_req = {}
        mask_write_req = {}
        for reg, value in device_table.read_requests.items():
            read_req[reg] = value[i]
        for reg, value in device_table.write_requests.items():
            write_req[reg] = value[i]
        for reg, value in device_table.mask_write_requests.items():
            mask_write_req[reg] = value[i]
        if type == 'Controller' and tsc_enable:
            gateway_dict[gw_ip].add_tsc(name, id, snc, read_req, write_req, mask_write_req)
        elif type == 'Meteo' and iwc_enable:
            gateway_dict[gw_ip].add_iwc(name, id, snc, read_req, write_req, mask_write_req)
        else: 
            print(f"Device {name} has a non admitted type: {type}")

def main() -> None:

    print(app_header)

    app_version = get_app_version()

    print("You are using the ReaderWriter version {}".format(app_version))
    print("Running update as principal.\n")

    init_config = InitFile()
    print("Loading configuration file...")
    config = init_config.load()
    tsc_enable = int(config["init_RW"]["tsc_enable"])
    iwc_enable = int(config["init_RW"]["iwc_enable"])
    max_threads = int(config["init_RW"]["maximum_threads"])
    threads_per_gw = int(config["init_RW"]["threads_per_gateway"])
    loop_time = int(config["init_RW"]["loop_time"])

    print("Loading devices...")
    devices_config_file, devices_config_table, devices_table, site = read_config_map()

    create_gateways(config, devices_table, tsc_enable, iwc_enable)

    sum_tsc = 0
    sum_iwc = 0
    for gateway in gateway_dict.values():
        if tsc_enable: sum_tsc = sum_tsc + gateway.get_tsc_num()
        else: print("TSCs' read/write is disabled")
        if iwc_enable: sum_iwc = sum_iwc + gateway.get_iwc_num()
        else: print("IWCs' read/write is disabled")

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

    report = Reporting(site)

    for gateway in gateway_dict.values():
        report.add_gateway(gateway)

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
