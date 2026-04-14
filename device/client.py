import os
import re
import logging
import logging.config
import logging.handlers
import time
from time import sleep

from pymodbus.client.sync import ModbusTcpClient, ModbusSocketFramer
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadBuilder
from pymodbus.exceptions import ModbusIOException
from datetime import datetime, timezone, timedelta

from common import common


def is_invalid_response(response, count):
    if response is None:
        return True
    if isinstance(response, ModbusIOException):
        return True
    if not hasattr(response, "registers"):
        return True
    return len(response.registers) != count

class Client:
    def __init__(
        self,
        config,
        name: str,
        id: int,
        snc: str,
        read_dict: dict,
        write_dict: dict,
        gateway_ip: str,
        port: int,
        rtu: type = ModbusSocketFramer,
        timeout: int = 2
    ) -> None:

        self.config = config
        self.id = id
        self.name = name
        self.snc = snc
        self.read_dict = read_dict
        self.write_dict = write_dict
        self.gateway_ip = gateway_ip
        self.port = port
        self.client = None
        self.rtu = rtu
        self.timeout = timeout
        self.error_attempt_count = 5
        self.error_attempt_time_ms = 10
        self.prod_id_init = "0"
        self.prod_id_sent = "0"
        self.prod_id_end = "0"
        self.comm_status = False
        self.start = False
        self.percent = 0
        self.full = False
        self.cs_received = 0
        self.cs_sent = 0
        self.apto = False
        self.bootloaded = False
        self.read = False
        self.written = False
        self.finished = False
        self.aborted = False
        self.read_errors = 0
        self.send_errors = 0
        self.local_date = datetime.now().strftime("%d/%m/%Y - %H:%M:%S")
        self.local_date_utc = datetime.now(timezone.utc).strftime("%d/%m/%Y - %H:%M:%S")
        self.duration = timedelta()
        self.iteration = 0
        self.mac = ""

        logging.config.fileConfig(
            os.path.join(common.CONFIG_DIR, "log.conf"), disable_existing_loggers=False)
        self.log = logging.getLogger('fw_updater')

    def connect(self) -> None:

        attempt = 0
        if not self.client.is_socket_open():
            self.log.debug(
                    "GW {}:{} - New socket created".format(
                        self.gateway_ip,
                        self.port,
                    )
                )
            time.sleep(5)
            while (not self.client.is_socket_open()
                   and attempt < self.error_attempt_count):
                attempt = attempt + 1
                self.client.connect()
                if not self.client.is_socket_open():
                    sleep(self.error_attempt_time_ms / 1000)
                self.log.debug(
                    "GW {}:{} - Modbus trying connect to gateway".format(
                        self.gateway_ip,
                        self.port,
                    )
                )
        if attempt > 0 and self.client.is_socket_open():
            self.log.debug(
                "GW {}:{} - Modbus connected.".format(
                    self.gateway_ip,
                    self.port,
                )
            )

    def read_register(self, address: int, count: int, unit: int) -> str:
        if not self.client or not self.client.is_socket_open():
            self.connect()
        attempt = 0
        response = self.client.read_holding_registers(
            address=address, count=count, unit=unit)
        while is_invalid_response(response, count) and attempt < 5:
            sleep(0.01)
            response = self.client.read_holding_registers(
                address=address, count=count, unit=unit)
            attempt = attempt + 1
        if is_invalid_response(response, count):
            raise ModbusIOException(
                "GW {}:{} - TSC: {}: There was a ModbusIOException.".format(
                    self.gateway_ip,
                    self.port,
                    unit
                )
            )
        return response

    def write_register_16bit(self, address: int, value: int, unit: int) -> str:
        if not self.client or not self.client.is_socket_open():
            self.connect()
        byte_order = Endian.Big
        word_order = Endian.Little
        builder = BinaryPayloadBuilder(
            byteorder=byte_order, wordorder=word_order, repack=False)
        builder.add_16bit_uint(int(value))
        builder = builder.to_registers()
        attempt = 0
        response = self.client.write_register(
            address=address, value=builder[0], unit=unit)
        while isinstance(response, ModbusIOException) and attempt < 5:
            sleep(0.01)
            response = self.client.write_register(
                address=address, value=builder[0], unit=unit)
            attempt = attempt + 1
        if isinstance(response, ModbusIOException):
            raise ModbusIOException(
                "GW {}:{} - TSC: {}: There was a ModbusIOException.".format(
                    self.gateway_ip,
                    self.port,
                    unit
                )
            )
        return response

    def write_register_32bit(self, address: str, value: int, unit: int) -> str:
        if not self.client or not self.client.is_socket_open():
            self.connect()
        byte_order = Endian.Big
        word_order = Endian.Little
        builder = BinaryPayloadBuilder(
            byteorder=byte_order, wordorder=word_order, repack=False)
        builder.add_32bit_uint(int(value))
        builder = builder.to_registers()
        attempt = 0
        response = self.client.write_registers(
            address=address, values=builder, unit=unit)
        while isinstance(response, ModbusIOException) and attempt < 5:
            sleep(0.01)
            response = self.client.write_registers(
                address=address, values=builder, unit=unit)
            attempt = attempt + 1
        if isinstance(response, ModbusIOException):
            message = "GW {}:{} - TSC: {}: There was a ModbusIOException"
            raise ModbusIOException(
                message.format(
                    self.gateway_ip,
                    self.port,
                    unit
                )
            )
        return response

    def close(self) -> None:
        if self.client:
            self.client.close()

    def add_firmware_status(self, new_firmware_version, product_id_init, product_id_sent, product_id_end, connected, percentage, checksum_sent, checksum_recv, bootloader, ended, read_errors, send_errors, tsc_local_date, tsc_utc_date, duration):
        if int(new_firmware_version, 0) == int(product_id_sent, 0): # Si sigo enviando la misma version cojo los valores, los dejo a default
            self.prod_id_sent = product_id_sent
            self.prod_id_init = product_id_init
            self.prod_id_end = product_id_end
            if connected == 'Yes':
                self.comm_status = True
            else:
                self.comm_status = False
            self.percent = percentage
            self.cs_sent = checksum_sent
            self.cs_received = checksum_recv
            if bootloader == 'Yes':
                self.bootloaded = True
            else:
                self.bootloaded = False
            if ended == 'Yes':
                self.finished = True
                self.percent = 100
            else:
                self.finished = False
            self.read_errors = read_errors
            self.send_errors = send_errors
            self.local_date = tsc_local_date
            self.local_date_utc = tsc_utc_date
            try:
                match = re.match(r"(?:(\d+) days? )?(\d+):(\d+):(\d+)", duration)
                days = int(match.group(1)) if match.group(1) else 0
                h, m, s = map(int, match.groups()[1:])
                self.duration = timedelta(days=days, hours=h, minutes=m, seconds=s)
            except Exception as e:
                self.duration = duration

    def get_id(self) -> int:
        return self.id

    def get_gateway_ip(self) -> str:
        return self.gateway_ip

    def get_prod_id_init(self) -> str:
        return self.prod_id_init

    def set_prod_id_init(self, prod_id_init: str) -> None:
        self.prod_id_init = hex(prod_id_init)

    def get_prod_id_sent(self) -> str:
        return self.prod_id_sent

    def set_prod_id_sent(self, prod_id_sent: str) -> None:
        self.prod_id_sent = hex(prod_id_sent)

    def get_prod_id_end(self) -> str:
        return self.prod_id_end

    def set_prod_id_end(self, prod_id_end: str) -> None:
        self.prod_id_end = hex(prod_id_end)

    def get_comm_status(self) -> bool:
        return self.comm_status

    def set_comm_status(self, comm_status: bool) -> None:
        self.comm_status = comm_status

    def get_start(self) -> bool:
        return self.start

    def set_start(self, start: bool) -> None:
        self.start = start

    def get_percent(self) -> float:
        return self.percent

    def set_percent(self, percent: float) -> None:
        self.percent = percent

    def get_full(self) -> bool:
        return self.full

    def set_full(self, full: bool) -> None:
        self.full = full

    def get_cs_received(self) -> int:
        return self.cs_received

    def set_cs_received(self, cs_received: int) -> None:
        self.cs_received = cs_received

    def get_cs_sent(self) -> int:
        return self.cs_sent

    def set_cs_sent(self, cs_sent: int) -> None:
        self.cs_sent = cs_sent

    def get_apto(self) -> bool:
        return self.apto

    def set_apto(self, apto: bool) -> None:
        self.apto = apto

    def get_bootloaded(self) -> bool:
        return self.bootloaded

    def set_bootloaded(self, bootloaded: bool) -> None:
        self.bootloaded = bootloaded

    def get_read(self) -> bool:
        return self.read

    def set_read(self, read: bool) -> None:
        self.read = read

    def get_written(self) -> bool:
        return self.written

    def set_written(self, written: bool) -> None:
        self.written = written

    def get_finished(self) -> bool:
        return self.finished

    def set_finished(self, finished: bool) -> None:
        self.finished = finished

    def get_aborted(self) -> bool:
        return self.aborted

    def set_aborted(self, aborted: bool) -> None:
        self.aborted = aborted

    def get_read_errors(self) -> int:
        return self.read_errors

    def set_read_errors(self, read_errors: int) -> None:
        self.read_errors = read_errors

    def get_sent_errors(self) -> int:
        return self.send_errors

    def set_sent_errors(self, sent_errors: int) -> None:
        self.send_errors = sent_errors

    def get_local_date(self) -> str:
        return self.local_date

    def set_local_date(self, local_date: str) -> None:
        self.local_date = local_date

    def get_local_date_utc(self) -> str:
        return self.local_date_utc

    def set_local_date_utc(self, local_date_utc: str) -> None:
        self.local_date_utc = local_date_utc

    def get_duration(self) -> int:
        return self.duration

    def set_duration(self, duration: timedelta) -> None:
        self.duration = duration

    def add_duration(self, duration: timedelta) -> None:
        try:
            self.duration += duration
        except Exception as e:
            self.duration = duration

    def get_iteration(self) -> int:
        return self.iteration

    def set_interation(self, iteration: int) -> None:
        self.iteration = iteration

    def add_interation(self, iteration: int) -> None:
        self.iteration += iteration

    def set_mac(self, mac: str) -> None:
        self.mac = mac

    def get_mac(self) -> str:
        return self.mac