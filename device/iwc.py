import tkinter as tk
from tkinter import messagebox

from time import sleep
from typing import List, Dict
from datetime import datetime, timezone
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder
from pymodbus.exceptions import ConnectionException, ModbusIOException

from common.init_file import InitFile
from common.firmware import Firmware
from device.client import Client
from device import iwc_modbus_map


class Iwc(Client):

    def get_register(self, register: str) -> int:
        data = self.read_register(
            int(register), 4, self.id)
        decoder = None
        registers = data.registers
        endian_order = Endian.Big
        word_endian_order = Endian.Little
        decoder = BinaryPayloadDecoder.fromRegisters(
            registers[0:1],
            byteorder=endian_order,
            wordorder=word_endian_order)
        decoded_data = (decoder.decode_16bit_uint())
        return decoded_data

    def set_register(self, register: str, value: int) -> int:
        result = self.write_register_16bit(
            int(register), int(value), self.id)
        if result:
            self.log.info(
                f"TSC {self.get_id()}: Register {register} was successfully set to {value}.")
            return True
        else:
            self.log.info(
                f"TSC {self.get_id()}: Register {register} was not set to {value}.")
            return False

    def get_firmware_version(self) -> int:
        data = self.read_register(
            iwc_modbus_map.IWC_FIRMWARE_PRODUCT_ID, 4, self.id)
        decoder = None
        registers = data.registers
        endian_order = Endian.Big
        word_endian_order = Endian.Little
        decoder = BinaryPayloadDecoder.fromRegisters(
            registers[0:1],
            byteorder=endian_order,
            wordorder=word_endian_order)
        decoded_data = (decoder.decode_16bit_uint() & 0xFF00) >> 8
        return decoded_data

    def get_firmware_product_id(self) -> int:
        data = self.read_register(
            iwc_modbus_map.IWC_FIRMWARE_PRODUCT_ID, 4, self.id)
        decoder = None
        registers = data.registers
        endian_order = Endian.Big
        word_endian_order = Endian.Little
        decoder = BinaryPayloadDecoder.fromRegisters(
            registers[0:1],
            byteorder=endian_order,
            wordorder=word_endian_order)
        decoded_data = (decoder.decode_16bit_uint())
        return decoded_data

    def get_firmware_crc_origin(self) -> int:
        data = self.read_register(
            iwc_modbus_map.IWC_FIRMWARE_CRC_BIN_ORIGIN, 4, self.id)
        decoder = None
        registers = data.registers
        endian_order = Endian.Big
        word_endian_order = Endian.Little
        decoder = BinaryPayloadDecoder.fromRegisters(
            registers[0:1],
            byteorder=endian_order,
            wordorder=word_endian_order)
        decoded_data = (decoder.decode_16bit_uint())
        return decoded_data

    def set_firmware_crc_origin(self, crc: int) -> None:
        result = self.write_register_16bit(
            iwc_modbus_map.IWC_FIRMWARE_CRC_BIN_ORIGIN, crc, self.id)
        if not result:
            self.log.debug("Cannot set firmware crc: {}".format(result))
        if result:
            self.log.debug(
                "Response firmware crc success: {}".format(result))

    def get_firmware_addr(self) -> int:
        data = self.read_register(
            iwc_modbus_map.IWC_FIRMWARE_BLOCK_POSITION, 4, self.id)
        decoder = None
        registers = data.registers
        endian_order = Endian.Big
        word_endian_order = Endian.Little
        decoder = BinaryPayloadDecoder.fromRegisters(
            registers[0:1],
            byteorder=endian_order,
            wordorder=word_endian_order)
        decoded_data = decoder.decode_16bit_uint()
        return decoded_data

    def get_firmware_crc_calculated(self) -> int:
        data = self.read_register(iwc_modbus_map.IWC_FIRMWARE_CRC_BIN_CALCULATED, 4, self.id)
        decoder = None
        registers = data.registers
        endian_order = Endian.Big
        word_endian_order = Endian.Little
        decoder = BinaryPayloadDecoder.fromRegisters(
            registers[0:1],
            byteorder=endian_order,
            wordorder=word_endian_order)
        decoded_data = (decoder.decode_16bit_uint())
        return decoded_data

    def set_firmware_crc_calculated(self, crc: int) -> int:
        result = self.write_register_16bit(
            iwc_modbus_map.IWC_FIRMWARE_CRC_BIN_CALCULATED, crc, self.id)
        if not result:
            self.log.debug("Cannot set firmware crc calculated: {}".format(result))
        if result:
            self.log.debug(
                "Response firmware crc calculated success: {}".format(result))

    def send_firmware_file_frame(self, address: int, frame: List[int]) -> bool:
        byte_order = Endian.Big
        word_order = Endian.Little
        builder = BinaryPayloadBuilder(
            byteorder=byte_order,
            wordorder=word_order,
            repack=False)
        builder.add_16bit_uint(int(address))
        builder = builder.to_registers()
        result = self.client.write_registers(
            address=iwc_modbus_map.IWC_FIRMWARE_BLOCK_POSITION,
            values=builder + frame,
            unit=self.id)

        if not result:
            self.log.debug("Cannot send firmware file: {}".format(result))
        if result:
            self.log.debug(
                "Response send firmware file success: {}".format(result))

        return True

    def check_vcc_level(self):
        data = self.read_register(iwc_modbus_map.IWC_FIRMWARE_VCC_MEASUREMENT_MV, 4, self.id)
        decoder = None
        registers = data.registers
        endian_order = Endian.Big
        word_endian_order = Endian.Little
        decoder = BinaryPayloadDecoder.fromRegisters(
            registers[0:1],
            byteorder=endian_order,
            wordorder=word_endian_order)
        decoded_data = (decoder.decode_16bit_uint())
        return decoded_data

    def launch_flag_update_fw(self) -> None:
        result = self.write_register_16bit(
            iwc_modbus_map.IWC_FIRMWARE_FLAG_UPDATE_FW, 0x55AA, self.id)
        if not result:
            self.log.debug("Cannot launch bootloader: {}".format(result))
        if result:
            self.log.debug(
                "Response launch bootloader success: {}".format(result))

    def read_write_device(self) -> None:
        attempts_wait_time = int(self.config["init_FW"]["attempts_wait_time"])
        max_iterations_per_device = int(self.config["init_FW"]["max_iterations_per_device"])

        if not self.get_finished() and self.iteration < max_iterations_per_device:
            try:
                self.connect()
                self.add_iteration()
                read = True
                written = True
                for read_key, value in self.read_dict.items():
                    if not isinstance(value, float) or pd.isna(value):
                        self.read_dict[read_key] = self.get_register(read_key.replace("Read_", ""))
                self.set_read(read)
                for write_key, value in self.write_dict.items():
                    try:
                        if self.set_register(write_key.replace("Write_", ""), value):
                            self.write_dict[write_key] = "OK"
                        else:
                            written = False
                        self.set_written(written)
                    except Exception as e:
                        self.log.debug(
                            f"GW {self.gateway_ip}, TSC {self.get_id()}: Cannot set register {write_key}={value}: {e}")

                if written and read:
                    self.set_finished(True)
                    self.log.info(
                        "GW {}, TSC {}: The data is up to date. Finished.".format(
                            self.gateway_ip, self.id))

            except ConnectionException:
                sleep(attempts_wait_time)
                self.log.warning("GW {}, TSC {}: Connection Lost. Retrying attempt: {}".format(
                    self.gateway_ip, self.id, self.get_iteration()))

            except ModbusIOException:
                sleep(attempts_wait_time)
                self.log.warning("GW {}, TSC {}: Modbus IO error. Retrying attempt: {}".format(
                    self.gateway_ip, self.id, self.get_iteration()))

            except Exception as e:
                sleep(attempts_wait_time)
                self.log.warning("GW {}, TSC {}:  Unknown Error -> {}. Retrying attempt: {}".format(
                    self.gateway_ip, self.id, e, self.get_iteration()))

            if self.iteration > max_iterations_per_device:
                self.log.error(
                    "GW {}, TSC {}: Too many retries. Aborting update process.".format(
                        self.gateway_ip, self.id))
                self.set_aborted(True)

    def verify(self, firmware: Dict[str, str]) -> None:
        max_iterations_per_device = int(self.config["init_FW"]["max_iterations_per_device"])
        result = False

        if self.iteration > max_iterations_per_device:
            self.set_aborted(True)
            result = True
        else:
            try:
                self.connect()

                product_id_end = self.get_firmware_product_id()
                self.set_prod_id_end(product_id_end)

                if int(firmware["version"]) == (product_id_end & 0xFF00) >> 8:
                    self.set_finished(True)
                    result = True

                #self.close()

            except ModbusIOException:
                self.log.warning("GW {}, IWC {}: Verification Modbus IO error.".format(
                    self.gateway_ip, self.id))
                self.iteration += 1

            except ConnectionException:
                self.log.warning("GW {}, IWC {}: Verification Connection Lost.".format(
                    self.gateway_ip, self.id))
                #self.close()
                self.iteration += 1

        return result
