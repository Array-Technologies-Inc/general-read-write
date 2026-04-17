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
        mask_write_dict: dict,
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
        self.mask_write_dict = mask_write_dict
        self.gateway_ip = gateway_ip
        self.port = port
        self.client = None
        self.rtu = rtu
        self.timeout = timeout
        self.error_attempt_count = 5
        self.error_attempt_time_ms = 10
        self.read = False
        self.written = False
        self.mask_written = False
        self.finished = False
        self.aborted = False
        self.iteration = 0

        logging.config.fileConfig(
            os.path.join(common.CONFIG_DIR, "log.conf"), disable_existing_loggers=False)
        self.log = logging.getLogger('reader_writer')

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

    def mask_write_register(self, address: int, and_mask: int, or_mask: int, unit: int) -> str:
        if not self.client or not self.client.is_socket_open():
            self.connect()
        attempt = 0
        response = self.client.mask_write_register(
            address=address, and_mask=and_mask, or_mask=or_mask, unit=unit)
        while isinstance(response, ModbusIOException) and attempt < 5:
            sleep(0.01)
            response = self.client.write_register(
            address=address, and_mask=and_mask, or_mask=or_mask, unit=unit)
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

    def get_id(self) -> int:
        return self.id

    def get_gateway_ip(self) -> str:
        return self.gateway_ip

    def get_comm_status(self) -> bool:
        return self.comm_status

    def set_comm_status(self, comm_status: bool) -> None:
        self.comm_status = comm_status

    def get_full(self) -> bool:
        return self.full

    def set_full(self, full: bool) -> None:
        self.full = full

    def get_read(self) -> bool:
        return self.read

    def set_read(self, read: bool) -> None:
        self.read = read

    def get_written(self) -> bool:
        return self.written

    def set_written(self, written: bool) -> None:
        self.written = written

    def get_mask_written(self) -> bool:
        return self.mask_written

    def set_mask_written(self, mask_written: bool) -> None:
        self.mask_written = mask_written

    def get_finished(self) -> bool:
        return self.finished

    def set_finished(self, finished: bool) -> None:
        self.finished = finished

    def get_aborted(self) -> bool:
        return self.aborted

    def set_aborted(self, aborted: bool) -> None:
        self.aborted = aborted

    def get_iteration(self) -> int:
        return self.iteration

    def set_interation(self, iteration: int) -> None:
        self.iteration = iteration

    def add_iteration(self) -> None:
        self.iteration += 1