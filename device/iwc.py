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

    def upgrade_device(self, firmware: Dict[str, str]) -> None:

        max_attempts = int(self.config["init_FW"]["max_attempts"])
        max_update_attempts = int(self.config["init_FW"]["max_update_attempts"])
        attempts_wait_time = int(self.config["init_FW"]["attempts_wait_time"])
        max_iterations_per_device = int(self.config["init_FW"]["max_iterations_per_device"])
        vcc_top_threshold = int(self.config["init_FW"]["vcc_top_threshold"])
        vcc_bottom_threshold = int(self.config["init_FW"]["vcc_bottom_threshold"])

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
                product_id_init = self.get_firmware_product_id()
                current_version = (product_id_init & 0xFF00) >> 8

                self.set_prod_id_init(product_id_init)
                self.set_prod_id_sent(new_version)
                self.set_comm_status(True)

                self.log.info("GW {}, IWC {}: Current version is {}, upgrading to version {}".format(
                    self.gateway_ip, self.id,
                    current_version, new_version))
                if current_version != new_version:

                    iwc_crc_origin = self.get_firmware_crc_origin()
                    crc_calculated = self.get_firmware_crc_calculated()
                    frame_array = Firmware.get_iwc_file_byte_array(firmware["path"])
                    new_crc = Firmware.get_file_crc(frame_array)
                    current_block = self.get_firmware_addr()
                    max_frames = len(frame_array)
                    if new_crc == iwc_crc_origin == crc_calculated:
                        frame = max_frames
                        self.log.debug("GW {}, TSC {}: crc already satisfied: {}".format(
                            self.gateway_ip, self.id,
                            new_crc))
                    elif (new_crc == iwc_crc_origin and
                        (10 < current_block < max_frames - 1)):
                        frame = current_block - 10
                    else:
                        self.set_firmware_crc_origin(new_crc)
                        frame = 0

                    self.set_cs_sent(new_crc)

                    current_block = self.get_firmware_addr()
                    self.log.debug("GW {}, TSC {}: new_crc_origin: {}, current_block: {}".format(
                        self.gateway_ip, self.id,
                        new_crc, current_block))

                    while frame < max_frames:
                        self.send_firmware_file_frame(frame, frame_array[frame])
                        self.log.info("GW {}, IWC {}: Address: {}/{} Reading: {}/{} = {:.2f}% Time: {}".format(  # noqa: E501
                                    self.gateway_ip, self.id,
                                    frame,  max_frames - 1,
                                    frame + 1, max_frames,
                                    frame * 100 / (max_frames - 1),
                                    datetime.now() - start))

                        self.set_percent(frame * 100 / (max_frames - 1))

                        frame += 1
                        sleep(.01)

                    if frame == max_frames:

                        self.set_full(True)
                        self.set_firmware_crc_calculated(0xaa55)
                        sleep(90)
                        crc_calculated = self.get_firmware_crc_calculated()
                        self.set_cs_received(crc_calculated)
                        self.set_percent(frame * 100 / max_frames)
                        self.log.debug("GW {}, IWC {}: crc_calculated: {}".format(
                            self.gateway_ip, self.id,
                            crc_calculated))

                        if new_crc == crc_calculated:
                            self.set_apto(True)

                            vcc = self.check_vcc_level()
                            aborted = False
                            validate_attempt = 0
                            validate = "no"
                            if vcc >= vcc_top_threshold:
                                validate = "yes"
                            elif vcc >= vcc_bottom_threshold:
                                try:
                                    root = tk.Tk()
                                    root.withdraw()
                                    while vcc >= vcc_bottom_threshold and not aborted and validate_attempt < 3:
                                        validate = messagebox.askquestion(
                                            "{} - IWC Validation".format(datetime.now().strftime("%d/%m/%Y - %H:%M:%S")),  # noqa: E501
                                            "GW {}, IWC {}: The VccMeasurement_mV(30028) value is over {}mV: {}mV, Do you want to continue?".format(  # noqa: E501
                                                self.gateway_ip, self.id, vcc_bottom_threshold, vcc))

                                        if validate.lower() == "yes":
                                            validate_attempt += 1

                                        elif validate.lower() == "no":
                                            self.log.warning("GW {}, IWC {}: Upgrade process aborted".format(
                                                self.gateway_ip, self.id))
                                            aborted = True

                                        else:
                                            self.log.warning("GW {}, IWC {}: Wrong value: '{}' Try again.".format(
                                                self.gateway_ip, self.id, validate))
                                            aborted = False
                                        vcc = self.check_vcc_level()
                                    root.destroy()
                                except Exception as e:
                                    update_attempts += 1
                                    self.log.error("GW {}, IWC {}: Failed to generate checking pop-ups".format(
                                        self.gateway_ip, self.id))
                            else:
                                validate = "no"

                            if validate.lower() == "yes":
                                self.log.warning("GW {}, IWC {}: Firmware Update Flag was sent with {}mV".format(
                                    self.gateway_ip, self.id, vcc))
                                self.launch_flag_update_fw()
                                self.set_bootloaded(True)

                                process_done = True
                            else:
                                self.log.error("GW {}, IWC {}: Firmware Update Flag will not be sent with {}mV".format(
                                    self.gateway_ip, self.id, vcc))
                        else:
                            update_attempts += 1
                            self.log.warning(
                                "GW {}, IWC {}: Update process failed. Checksum error. Retrying attempt: {}".format(
                                    self.gateway_ip, self.id, update_attempts))
                else:
                    self.log.info(
                        "GW {}, IWC {}: The firmware v{} is already installed. Finishing.".format(
                            self.gateway_ip, self.id, current_version))
                    self.set_finished(True)
                    process_done = True

            except ConnectionException:
                attempts += 1
                sleep(attempts_wait_time)
                self.log.warning("GW {}, IWC {}: Connection Lost. Retrying attempt: {}".format(
                    self.gateway_ip, self.id, attempts))
                sent_errors += 1
                self.set_sent_errors(sent_errors)

            except ModbusIOException:
                attempts += 1
                sleep(attempts_wait_time)
                self.log.warning("GW {}, IWC {}: Modbus IO error. Retrying attempt: {}".format(  # noqa: E501
                    self.gateway_ip, self.id, attempts))
                sent_errors += 1
                self.set_sent_errors(sent_errors)

            except Exception as e:
                attempts += 1
                sleep(attempts_wait_time)
                self.log.warning("GW {}, IWC {}: Unknown Error -> {}".format(
                    self.gateway_ip, self.id, e))
                self.set_sent_errors(sent_errors)

        self.iteration += 1
        self.add_duration(datetime.now() - start)
        #self.close()

        if attempts >= max_attempts or update_attempts >= max_update_attempts:
            self.log.error(
                "GW {}, IWC {}: Too many retries. Finishing update process.".format(
                    self.gateway_ip, self.id))
        if self.iteration > max_iterations_per_device:
            self.log.error(
                "GW {}, IWC {}: Too many retries. Aborting update process.".format(
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
                self.log.warning("GW {}, IWC {}: Verification Modbus IO error.".format(
                    self.gateway_ip, self.id))
                self.iteration += 1

            except ConnectionException:
                self.log.warning("GW {}, IWC {}: Verification Connection Lost.".format(
                    self.gateway_ip, self.id))
                #self.close()
                self.iteration += 1

        return result
