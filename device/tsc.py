from time import sleep
from typing import List, Tuple, Dict
from datetime import datetime, timezone
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder
from pymodbus.exceptions import ConnectionException, ModbusIOException

from common import common
from common.init_file import InitFile
from common.firmware import Firmware
from device.client import Client
from device import tsc_modbus_map


class Tsc(Client):

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
                f"TSC{self.get_id()}: Register {register} was successfully set to {value}.")
            return True
        else:
            self.log.info(
                f"TSC{self.get_id()}: Register {register} was not set to {value}.")
            return False


    def get_firmware_version(self) -> int:
        data = self.read_register(
            tsc_modbus_map.PRODUCTID, 4, self.id)
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
            tsc_modbus_map.PRODUCTID, 4, self.id)
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

    def get_firmware_new_version(self) -> int:
        data = self.read_register(
            tsc_modbus_map.STI_FIRMWARE_NEW_VERSION, 4, self.id)
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

    def set_firmware_new_version(self, version: int) -> None:
        result = self.write_register_16bit(
            tsc_modbus_map.STI_FIRMWARE_NEW_VERSION, version, self.id)
        if result:
            self.log.debug(
                "Response firmware new version success: {}".format(result))

    def get_firmware_enable_change(self) -> int:
        data = self.read_register(
            tsc_modbus_map.STI_FIRMWARE_ENABLE_CHANGE, 4, self.id)
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

    def set_firmware_enable_change(self, value: int) -> None:
        result = self.write_register_16bit(
            tsc_modbus_map.STI_FIRMWARE_ENABLE_CHANGE, value, self.id)
        if result:
            self.log.debug(
                "Response firmware change enable success: {}".format(result))

    def get_firmware_size(self) -> int:
        data = self.read_register(tsc_modbus_map.STI_FIRMWARE_SIZE, 4, self.id)
        decoder = None
        registers = data.registers
        endian_order = Endian.Big
        word_endian_order = Endian.Little
        decoder = BinaryPayloadDecoder.fromRegisters(
            registers[0:2],
            byteorder=endian_order,
            wordorder=word_endian_order)
        decoded_data = decoder.decode_32bit_uint()
        return decoded_data

    def set_firmware_size(self, size: int) -> None:
        result = self.write_register_32bit(
            tsc_modbus_map.STI_FIRMWARE_SIZE, size, self.id)
        if not result:
            self.log.debug("Cannot set firmware size: {}".format(result))
        if result:
            self.log.debug("Response firmware size success: {}".format(result))

    def get_firmware_checksum8bit(self) -> int:
        data = self.read_register(
            tsc_modbus_map.STI_FIRMWARE_CHECKSUM8BIT, 4, self.id)
        decoder = None
        registers = data.registers
        endian_order = Endian.Big
        word_endian_order = Endian.Little
        decoder = BinaryPayloadDecoder.fromRegisters(
            registers[0:1],
            byteorder=endian_order,
            wordorder=word_endian_order)
        decoded_data = decoder.decode_16bit_uint() & 0x00FF
        return decoded_data

    def set_firmware_checksum8bit(self, checksum: int) -> None:
        checksum8bit = (common.NUM_REGS_FRM_TSC << 8) | checksum
        result = self.write_register_16bit(
            tsc_modbus_map.STI_FIRMWARE_CHECKSUM8BIT, checksum8bit, self.id)
        if not result:
            self.log.debug("Cannot set firmware checksum8bit: {}".format(result))
        if result:
            self.log.debug(
                "Response firmware checksum8bit success: {}".format(result))

    def get_initial_status(self) -> Tuple:
        data = self.read_register(tsc_modbus_map.STI_FIRMWARE_NEW_VERSION, 4, self.id)
        registers = data.registers
        endian_order = Endian.Big
        word_endian_order = Endian.Little

        decoder_firm_new_version = BinaryPayloadDecoder.fromRegisters(
            registers[0:1],
            byteorder=endian_order,
            wordorder=word_endian_order)
        firm_new_version = decoder_firm_new_version.decode_16bit_uint()

        decoder_firm_new_size = BinaryPayloadDecoder.fromRegisters(
            registers[1:3],
            byteorder=endian_order,
            wordorder=word_endian_order)
        firm_new_size = decoder_firm_new_size.decode_32bit_uint()

        decoder_firm_checksum8bit = BinaryPayloadDecoder.fromRegisters(
            registers[3:4],
            byteorder=endian_order,
            wordorder=word_endian_order)
        firm_checksum8bit = decoder_firm_checksum8bit.decode_16bit_uint() & 0x00FF

        return (firm_new_version, firm_new_size, firm_checksum8bit)

    def get_firmware_nf_2(self) -> int:
        data = self.read_register(tsc_modbus_map.NF_2, 4, self.id)
        decoder = None
        registers = data.registers
        endian_order = Endian.Big
        word_endian_order = Endian.Little
        decoder = BinaryPayloadDecoder.fromRegisters(
            registers[0:1],
            byteorder=endian_order,
            wordorder=word_endian_order)
        decoded_data = decoder.decode_16bit_uint() & 0x00FF
        return decoded_data

    def get_firmware_nf_perc(self) -> int:
        data = self.read_register(tsc_modbus_map.NF_PERC, 4, self.id)
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

    def get_firmware_addr_esperada(self) -> int:
        data = self.read_register(
            tsc_modbus_map.STI_FIRMWARE_ADDR_ESPERADA, 4, self.id)
        decoder = None
        registers = data.registers
        endian_order = Endian.Big
        word_endian_order = Endian.Little
        decoder = BinaryPayloadDecoder.fromRegisters(
            registers[0:2],
            byteorder=endian_order,
            wordorder=word_endian_order)
        decoded_data = decoder.decode_32bit_uint()
        return decoded_data

    def set_firmware_addr_esperada(self, value: int) -> None:
        result = self.write_register_32bit(
            tsc_modbus_map.STI_FIRMWARE_ADDR_ESPERADA, value, self.id)
        if not result:
            self.log.debug("Cannot set expected addr: {}".format(result))
        if result:
            self.log.debug("Response expected addr success: {}".format(result))

    def get_firmware_addr(self) -> int:
        data = self.read_register(
            tsc_modbus_map.STI_FIRMWARE_ADDR, 4, self.id)
        decoder = None
        registers = data.registers
        endian_order = Endian.Big
        word_endian_order = Endian.Little
        decoder = BinaryPayloadDecoder.fromRegisters(
            registers[0:2],
            byteorder=endian_order,
            wordorder=word_endian_order)
        decoded_data = decoder.decode_32bit_uint()
        return decoded_data

    def set_firmware_addr(self, value: int) -> None:
        result = self.write_register_32bit(
            tsc_modbus_map.STI_FIRMWARE_ADDR, value, self.id)
        if not result:
            self.log.debug("Cannot set firmware addr: {}".format(result))
        if result:
            self.log.debug("Response firmware addr success: {}".format(result))

    def get_firmware_addr_and_addr_esperada(self) -> Tuple:
        data = self.read_register(
            tsc_modbus_map.STI_FIRMWARE_ADDR_ESPERADA, 4, self.id)
        decoder_addr = None
        registers = data.registers
        endian_order = Endian.Big
        word_endian_order = Endian.Little
        decoder_addr_esperada = BinaryPayloadDecoder.fromRegisters(
            registers[0:2],
            byteorder=endian_order,
            wordorder=word_endian_order)
        addr_esperada = decoder_addr_esperada.decode_32bit_uint()
        decoder_addr = BinaryPayloadDecoder.fromRegisters(
            registers[2:4],
            byteorder=endian_order,
            wordorder=word_endian_order)
        addr = decoder_addr.decode_32bit_uint()

        return (addr_esperada, addr)

    def send_firmware_file_frame(self, address: int, frame: List[int]) -> bool:
        if not self.client or not self.client.is_socket_open():
            self.connect()
        byte_order = Endian.Big
        word_order = Endian.Little
        builder = BinaryPayloadBuilder(
            byteorder=byte_order,
            wordorder=word_order,
            repack=False)
        builder.add_32bit_uint(int(address))
        builder = builder.to_registers()
        result = self.client.write_registers(
            address=tsc_modbus_map.STI_FIRMWARE_ADDR,
            values=builder + frame,
            unit=self.id)

        if not result:
            self.log.debug("Cannot send firmware file: {}".format(result))
        if result:
            self.log.debug(
                "Response send firmware file success: {}".format(result))

        return True

    def launch_bootloader(self) -> None:
        result = self.write_register_16bit(
            tsc_modbus_map.AIN_ENTRADA_BOOTLOADER, 1, self.id)
        if not result:
            self.log.debug("Cannot launch bootloader: {}".format(result))
        if result:
            self.log.debug(
                "Response launch bootloader success: {}".format(result))

    def reset(self) -> None:
        self.set_firmware_enable_change(0)
        self.set_firmware_addr_esperada(0xFFFFF)

    def upgrade_device(self, firmware: Dict[str, str]) -> None:
        max_attempts = int(self.config["init_FW"]["max_attempts"])
        max_equal_addr_attempts = int(self.config["init_FW"]["max_equal_addr_attempts"])
        max_update_attempts = int(self.config["init_FW"]["max_update_attempts"])
        attempts_wait_time = int(self.config["init_FW"]["attempts_wait_time"])
        equal_addr_attempts_wait_time = int(self.config["init_FW"]["equal_addr_attempts_wait_time"])
        max_iterations_per_device = int(self.config["init_FW"]["max_iterations_per_device"])

        process_done = False
        attempts = 0
        update_attempts = 0
        sent_errors = 0
        if not self.start:
            self.start = True
            self.local_date = datetime.now().strftime("%d/%m/%Y - %H:%M:%S")
            self.local_date_utc = datetime.now(timezone.utc).strftime("%d/%m/%Y - %H:%M:%S")
        start = datetime.now()
        if not self.get_finished() and self.iteration < max_iterations_per_device:
            try:
                self.connect()
                read = True
                written = True
                for read_key, value in self.read_dict.items():
                    if not isinstance(value, int):
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
                        self.log.debug(f"TSC{self.get_id()}: Cannot set register {write_key}={value}: {e}")

                if written and read:
                    self.set_finished(True)
                    self.log.info(
                        "GW {}, TSC {}: The data is up to date. Finished.".format(
                            self.gateway_ip, self.id))

            except ConnectionException:
                attempts += 1
                sleep(attempts_wait_time)
                self.log.warning("GW {}, TSC {}: Connection Lost. Retrying attempt: {}".format(
                    self.gateway_ip, self.id, attempts))
                sent_errors += 1
                self.set_sent_errors(sent_errors)

            except ModbusIOException:
                attempts += 1
                sleep(attempts_wait_time)
                self.log.warning("GW {}, TSC {}: Modbus IO error. Retrying attempt: {}".format(
                    self.gateway_ip, self.id, attempts))
                sent_errors += 1
                self.set_sent_errors(sent_errors)

            except Exception as e:
                attempts += 1
                sleep(attempts_wait_time)
                self.log.warning("GW {}, TSC {}: Unknown Error -> {}".format(
                    self.gateway_ip, self.id, e))
                self.set_sent_errors(sent_errors)

        self.iteration += 1

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
                self.log.warning("GW {}, TSC {}: Verification Modbus IO error.".format(
                    self.gateway_ip, self.id))
                self.iteration += 1

            except ConnectionException:
                self.log.warning("GW {}, TSC {}: Verification Connection Lost.".format(
                    self.gateway_ip, self.id))
                #self.close()
                self.iteration += 1

        return result
