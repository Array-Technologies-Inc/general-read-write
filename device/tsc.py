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
            register, 4, self.id)
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
        while ((not process_done) and
                attempts < max_attempts and
                update_attempts < max_update_attempts and
                self.iteration < max_iterations_per_device):
            try:
                self.connect()
                new_version = int(firmware["version"])
                for read in self.read_dict:
                    self.read_dict[read.key] = self.get_register(read.key)
                product_id_init = self.get_firmware_product_id()
                current_version = (product_id_init & 0xFF00) >> 8

                self.set_prod_id_init(product_id_init)
                self.set_prod_id_sent(new_version)
                self.set_comm_status(True)

                self.log.info("GW {}, TSC {}: Current version is v{}, upgrading to version v{}".format(  # noqa: E501
                    self.gateway_ip, self.id,
                    current_version, new_version))
                if current_version != new_version:

                    frame_array = Firmware.get_tsc_file_byte_array(firmware["path"])
                    new_size = Firmware.get_file_size(firmware["path"])
                    new_checksum = Firmware.get_file_checksum(firmware["path"])
                    max_frames = len(frame_array)

                    (tsc_new_version, tsc_new_size, tsc_checksum8bit) = self.get_initial_status()
                    tsc_nf_perc = self.get_firmware_nf_perc()
                    (firm_addr_esp, firm_addr) = self.get_firmware_addr_and_addr_esperada()

                    self.log.debug("GW {}, TSC {}: new_version: {}, checksum8bit: {}, new_size: {}, nf_perc: {}, firm_addr: {}, firm_addr_esp: {}".format(  # noqa: E501
                        self.gateway_ip, self.id,
                        tsc_new_version, tsc_checksum8bit, tsc_new_size,
                        tsc_nf_perc, firm_addr, firm_addr_esp))

                    if (tsc_new_version == int(new_version) and
                            tsc_checksum8bit == new_checksum and
                            tsc_new_size == new_size and
                            tsc_nf_perc != 1000 and
                            firm_addr != 32
                            and firm_addr_esp != 0xFFFFF):
                        self.log.info("GW {}, TSC {}: Continue previous update process".format(
                            self.gateway_ip, self.id))
                        self.set_firmware_enable_change(1)

                    else:
                        self.log.info("GW {}, TSC {}: Starting new update process".format(
                            self.gateway_ip, self.id))
                        self.reset()
                        self.set_firmware_enable_change(1)
                        self.set_firmware_new_version(new_version)
                        self.set_firmware_size(new_size)
                        self.set_firmware_checksum8bit(new_checksum)

                    self.set_cs_sent(new_checksum)

                    (firm_addr_esp, firm_addr) = self.get_firmware_addr_and_addr_esperada()
                    frame = int((firm_addr_esp - 32) / (common.NUM_REGS_FRM_TSC * 2))

                    attempts = 0
                    equal_addr_attempts = 0

                    self.set_start(True)
                    while frame < max_frames and equal_addr_attempts < max_equal_addr_attempts:
                        self.send_firmware_file_frame(firm_addr_esp, frame_array[frame])
                        (firm_addr_esp, firm_addr) = self.get_firmware_addr_and_addr_esperada()

                        if firm_addr == firm_addr_esp:
                            sleep(equal_addr_attempts_wait_time)
                            equal_addr_attempts += 1
                            sent_errors += 1
                            self.set_sent_errors(sent_errors)
                            self.log.warning(
                                "GW {}, TSC {}: Retrying equal expected addr attempt: {}".format(
                                    self.gateway_ip, self.id, equal_addr_attempts))

                        else:
                            equal_addr_attempts = 0

                        self.log.info("GW {}, TSC {}: Address: {}/{} Reading: {}/{} = {:.2f}% Time: {}".format(  # noqa: E501
                            self.gateway_ip, self.id, firm_addr, new_size,
                            frame + 1, max_frames, (frame + 1) * 100 / max_frames,
                            datetime.now() - start))

                        self.set_percent((frame + 1) * 100 / max_frames)

                        frame = int((firm_addr_esp - 32) / (common.NUM_REGS_FRM_TSC * 2))

                        self.log.debug("GW {}, TSC {}: attempts: {}, update_attempts: {}, process_done: {}, equal_addr_attempts: {}, frame: {}, firm_addr: {}, firm_addr_esp: {}".format(  # noqa: E501
                            self.gateway_ip, self.id,
                            attempts, update_attempts, process_done,
                            equal_addr_attempts, frame, firm_addr, firm_addr_esp))

                    if equal_addr_attempts < max_equal_addr_attempts:
                        self.set_firmware_enable_change(0)
                        checksum_calculated = self.get_firmware_nf_2()
                        self.set_cs_received(checksum_calculated)
                        percent_received = self.get_firmware_nf_perc()
                        self.set_percent(percent_received / 10)

                        self.log.debug("GW {}, TSC {}: checksum_calculated: {}, percent_received: {}".format(  # noqa: E501
                            self.gateway_ip, self.id,
                            checksum_calculated, percent_received))

                        if percent_received == 1000:
                            self.set_full(True)

                        if new_checksum == checksum_calculated and percent_received == 1000:
                            self.set_apto(True)
                            self.launch_bootloader()
                            self.log.info("GW {}, TSC {}: Bootloader launched".format(
                                self.gateway_ip, self.id))
                            self.set_bootloaded(True)
                            process_done = True
                        else:
                            update_attempts += 1
                            self.log.warning(
                                "GW {}, TSC {}: Update process failed. Retrying attempt: {}".format(
                                    self.gateway_ip, self.id, update_attempts))
                    else:
                        update_attempts += 1
                        self.log.warning(
                            "GW {}, TSC {}: Update process failed. Retrying equal expected addr attempt: {}".format(  # noqa: E501
                                self.gateway_ip, self.id, update_attempts))

                else:
                    self.log.info(
                        "GW {}, TSC {}: The firmware v{} is already installed. Finishing.".format(
                            self.gateway_ip, self.id, current_version))
                    self.set_finished(True)
                    process_done = True

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
        self.add_duration(datetime.now() - start)
        #self.close()

        if attempts >= max_attempts or update_attempts >= max_update_attempts:
            self.log.error(
                "GW {}, TSC {}: Too many retries. Finishing update process.".format(
                    self.gateway_ip, self.id))
        if self.iteration > max_iterations_per_device:
            self.log.error(
                "GW {}, TSC {}: Too many retries. Aborting update process.".format(
                    self.gateway_ip, self.id))
            self.iteration = 0
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
