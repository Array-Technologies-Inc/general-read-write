import os
import logging
import logging.config
import logging.handlers
from time import sleep
from typing import List, Dict
from threading import Thread
from queue import Empty, Queue
from pymodbus.client.sync import ModbusTcpClient, ModbusSocketFramer
import socket

from common import common
from device.iwc import Iwc
from device.tsc import Tsc

from datetime import datetime, timezone, timedelta

logging.config.fileConfig(os.path.join(common.CONFIG_DIR, "log.conf"), disable_existing_loggers=False)  # noqa: E501
log = logging.getLogger('fw_updater')


class Gateway(Thread):

    def __init__(self, ip: str, config) -> None:  # noqa: E501
        Thread.__init__(self)
        self.ip = ip
        self.config = config
        self.port = config["init_FW"]["gw_port"]
        self.client = None
        self.timeout = 3

        self.new_tsc_version = None
        self.tsc_num = 0
        self.tsc_full = 0
        self.tsc_aborted = 0
        self.tsc_list = {}

        self.new_iwc_version = None
        self.iwc_num = 0
        self.iwc_full = 0
        self.iwc_aborted = 0
        self.iwc_list = {}
        self.tsc_queue = Queue()
        self.iwc_queue = Queue()

        self.threads = []
        self.threads_per_gateway = int(config["init_FW"]["threads_per_gateway"])
        self.max_iterations = int(config["init_FW"]["max_iterations"])
        self.mac_file_updated = False

        self.process_finished = False

    def set_mac_file_updated(self, mac_file_updated) -> bool:
        self.mac_file_updated = mac_file_updated

    def get_mac_file_updated(self) -> bool:
        return self.mac_file_updated

    def get_ip(self) -> None:
        return self.ip

    def get_port(self) -> None:
        return self.port

    def add_tsc(self, tsc_name: str, tsc_id: int, tsc_snc: str, read_dict: dict, write_dict: dict,  product_id_init: str, product_id_sent: str, product_id_end: str, connected: str, percentage: float, checksum_sent: int, checksum_recv: int, bootloader: str, ended: str, read_errors: int, send_errors: int, tsc_local_date: datetime, tsc_utc_date: datetime, duration: timedelta) -> None:
        tsc = Tsc(self.config, tsc_name, tsc_id, tsc_snc, read_dict, write_dict, self.ip, self.port)
        try:
            tsc.add_firmware_status(self.new_tsc_version['version'], product_id_init, product_id_sent, product_id_end, connected, percentage, checksum_sent, checksum_recv, bootloader, ended, read_errors, send_errors, tsc_local_date, tsc_utc_date, duration)
        except Exception as e:
            pass
        self.tsc_list[tsc_id] = tsc
        self.tsc_queue.put(tsc)
        self.tsc_num = len(self.tsc_list)

    def get_tsc_list(self) -> List[Tsc]:
        return self.tsc_list

    def get_tsc_keys(self) -> List[int]:
        return self.tsc_list.keys()

    def get_tsc_num(self) -> int:
        return self.tsc_num

    def get_full_tsc(self) -> int:
        return self.tsc_full

    def get_aborted_tsc(self) -> int:
        return self.tsc_aborted

    def add_new_tcs_version(self, firmware: List[Dict[str, str]]) -> None:
        self.new_tsc_version = firmware

    def add_iwc(self, iwc_name: str, iwc_id: int, iwc_snc: str, product_id_init: str, product_id_sent: str, product_id_end: str, connected: str, percentage: float, checksum_sent: int, checksum_recv: int, bootloader: str, ended: str, read_errors: int, send_errors: int, tsc_local_date: datetime, tsc_utc_date: datetime, duration: timedelta) -> None:
        iwc = Iwc(self.config, iwc_name, iwc_id, iwc_snc, self.ip, self.port)
        try:
            iwc.add_firmware_status(self.new_iwc_version['version'], product_id_init, product_id_sent, product_id_end, connected, percentage, checksum_sent, checksum_recv, bootloader, ended, read_errors, send_errors, tsc_local_date, tsc_utc_date, duration)
        except Exception as e:
            pass
        self.iwc_list[iwc_id] = iwc
        self.iwc_queue.put(iwc)
        self.iwc_num = len(self.iwc_list)

    def get_iwc_list(self) -> List[Iwc]:
        return self.iwc_list

    def get_iwc_keys(self) -> List[int]:
        return self.iwc_list.keys()

    def get_iwc_num(self) -> int:
        return self.iwc_num

    def get_full_iwc(self) -> int:
        return self.iwc_full

    def set_full_iwc(self, full_iwc: int) -> None:
        self.iwc_full = full_iwc

    def get_aborted_iwc(self) -> int:
        return self.iwc_aborted

    def set_aborted_iwc(self, aborted_iwc: int) -> None:
        self.iwc_aborted = aborted_iwc

    def add_new_iwc_version(self, firmware: List[Dict[str, str]]) -> None:
        self.new_iwc_version = firmware

    def upgrade_tsc(self, tsc_id: int, firmware: Dict[str, str]) -> None:
        self.tsc_list[tsc_id].upgrade_device(firmware)

    def upgrade_iwc(self, iwc_id: int, firmware: Dict[str, str]) -> None:
        self.iwc_list[iwc_id].upgrade_device(firmware)

    def upgrade_all_devices(self, iwc_firmware, tsc_firmware):
        iteration = 0
        try:
            self.client = ModbusTcpClient(
                self.ip, self.port, ModbusSocketFramer, timeout=self.timeout)
            self.client.socket = socket.create_connection(
                    (self.ip, self.port),
                    timeout=self.timeout,
                    source_address=("", 0),
                    all_errors=False)
            self.client.connect()
            log.info(f"GW {self.ip} open a socket on port {self.port}")
        except Exception as e:
            log.error(f"GW {self.ip} cannot open a socket on port {self.port}: {e}")

        if self.client.is_socket_open():
            self.verify_iwc()
            self.verify_tsc()
            while ((iteration < self.max_iterations) and ((self.tsc_aborted + self.tsc_full < self.get_tsc_num()) or (self.iwc_aborted + self.iwc_full < self.get_iwc_num()))):
                if not self.iwc_queue.empty():
                    iwc = self.iwc_queue.get()
                    iwc_id = iwc.get_id()
                    if ((iwc_firmware is not None) and
                        (not self.iwc_list[iwc_id].get_bootloaded() and not
                            (self.iwc_list[iwc_id].get_finished() or self.iwc_list[iwc_id].get_aborted()))):
                        self.iwc_list[iwc_id].client = self.client
                        self.upgrade_iwc(iwc_id, iwc_firmware)
                    self.iwc_queue.task_done()
                elif not self.tsc_queue.empty():
                    tsc = self.tsc_queue.get()
                    tsc_id = tsc.get_id()
                    if ((tsc_firmware is not None) and
                        (not self.tsc_list[tsc_id].get_bootloaded() and not
                            (self.tsc_list[tsc_id].get_finished() or self.tsc_list[tsc_id].get_aborted()))):
                        self.tsc_list[tsc_id].client = self.client
                        self.upgrade_tsc(tsc_id, tsc_firmware)
                    self.tsc_queue.task_done()
                else:
                    self.verify_iwc()
                    self.verify_tsc()
                    log.info(f"GW {self.ip}, Iteration {iteration} finished: IWC F|A|T {self.iwc_full}|{self.iwc_aborted}|{self.get_iwc_num()} \tTSC F|A|T  {self.tsc_full}|{self.tsc_aborted}|{self.get_tsc_num()}")

                iteration += 1

            log.error(f"GW {self.ip}, Cycle finished. \tIWC F|A|T {self.iwc_full}|{self.iwc_aborted}|{self.get_iwc_num()} \tTSC F|A|T  {self.tsc_full}|{self.tsc_aborted}|{self.get_tsc_num()}")
            try:
                self.client.close()
            except Exception as e:
                log.error(
                        "GW{} - Cannot close one socket".format(
                            self.ip))
        iteration += 10000

        if not ((self.tsc_aborted + self.tsc_full < self.get_tsc_num()) or (self.iwc_aborted + self.iwc_full < self.get_iwc_num())):
            self.process_finished = True
            log.error(f"GW {self.ip}, No device pending update. \tIWC F|A|T {self.iwc_full}|{self.iwc_aborted}|{self.get_iwc_num()} \tTSC F|A|T  {self.tsc_full}|{self.tsc_aborted}|{self.get_tsc_num()}")

    def verify_tsc(self):
        self.tsc_full = 0
        self.tsc_aborted = 0
        for tsc in self.get_tsc_list():
            self.tsc_list[tsc].client = self.client
            if (self.tsc_list[tsc].get_bootloaded() and
                not (self.tsc_list[tsc].get_finished() or
                     self.tsc_list[tsc].get_aborted())):
                result = self.tsc_list[tsc].verify(self.new_tsc_version)
                if result:
                    self.tsc_full += 1
            elif self.tsc_list[tsc].get_finished():
                self.tsc_full += 1
            elif self.tsc_list[tsc].get_aborted():
                self.tsc_aborted += 1
            else:
                self.tsc_queue.put(self.tsc_list[tsc])

    def verify_iwc(self):
        self.iwc_full = 0
        self.iwc_aborted = 0
        for iwc in self.get_iwc_list():
            self.iwc_list[iwc].client = self.client
            if (self.iwc_list[iwc].get_bootloaded() and
                not (self.iwc_list[iwc].get_finished() or
                     self.iwc_list[iwc].get_aborted())):
                result = self.iwc_list[iwc].verify(self.new_iwc_version)
                if result:
                    self.iwc_full += 1
            elif self.iwc_list[iwc].get_finished():
                self.iwc_full += 1
            elif self.iwc_list[iwc].get_aborted():
                self.iwc_aborted += 1
            else:
                self.iwc_queue.put(self.iwc_list[iwc])

    def run(self):
        threads = []
        # Run the threads
        for i in range(1, self.threads_per_gateway + 1):
            if not self.process_finished:
                try:
                    gw_thread = Thread(target=self.upgrade_all_devices, args=(self.new_iwc_version, self.new_tsc_version))
                    threads.append(gw_thread)
                    log.warning(f"{gw_thread} launched")
                    gw_thread.start()
                except Exception as e:
                    log.error(
                        "GW{} - Thread cannot run {}".format(
                            self.ip, e))

        # Check if the threads are not working
        while not self.process_finished:
            for i, gw_thread in enumerate(threads):
                if not gw_thread.is_alive():
                    log.error(f"{gw_thread} closed")
                    del threads[i]
                    try:
                        gw_thread = Thread(target=self.upgrade_all_devices, args=(self.new_iwc_version, self.new_tsc_version))
                        threads.append(gw_thread)
                        gw_thread.start()
                        log.error(f"{gw_thread} launched")
                    except Exception as e:
                        log.error(
                            "GW {} - Thread cannot run {}".format(
                                self.ip, e))

            sleep(10)

        log.error(f"GW {self.ip} Updating process is finished")



