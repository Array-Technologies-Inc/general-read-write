from os import write
import pandas as pd
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

    def get_register(self, register: str, type = "U16") -> int:
        data = self.read_register(
            int(register), 4, self.id)
        decoder = None
        registers = data.registers
        endian_order = Endian.Big
        word_endian_order = Endian.Little
        if type =="F32":
            decoder = BinaryPayloadDecoder.fromRegisters(
                registers[0:2],
                byteorder=endian_order,
                wordorder=word_endian_order)
            decoded_data = (decoder.decode_32bit_float())
        elif type =="S16":
            decoder = BinaryPayloadDecoder.fromRegisters(
                registers[0:1],
                byteorder=endian_order,
                wordorder=word_endian_order)
            decoded_data = (decoder.decode_16bit_int())
        else:
            decoder = BinaryPayloadDecoder.fromRegisters(
                registers[0:1],
                byteorder=endian_order,
                wordorder=word_endian_order)
            decoded_data = (decoder.decode_16bit_uint())
        return decoded_data

    def set_register(self, register: str, value, type = "U16") -> int:
        if type == "F32":
            value = float(value)
            result = self.write_register_32bit(
                int(register), value, self.id)
        else:
            value = int(value)
            result = self.write_register_16bit(
                int(register), value, self.id, type)
        if result and not result.isError():
            self.log.info(
                f"GW {self.gateway_ip}, TSC {self.get_id()}: Register {register} was successfully set to {value}.")
            return True
        elif result.isError():
            self.log.info(
                f"GW {self.gateway_ip}, TSC {self.get_id()}: Register {register} was NOT set to {value}: {result}")
            return False
        else:
            self.log.info(
                f"GW {self.gateway_ip}, TSC {self.get_id()}: Register {register} was NOT set to {value}.")
            return False

    def set_mask_register(self, register: str, and_mask: int, or_mask: int) -> int:
        result = self.mask_write_register(
            int(register), and_mask, or_mask, self.id)
        if result and not result.isError():
            self.log.info(
                f"GW {self.gateway_ip}, TSC {self.get_id()}: Register {register} was successfully set to mask {and_mask}|{or_mask}.")
            return True
        elif result.isError():
            self.log.info(
                f"GW {self.gateway_ip}, TSC {self.get_id()}: Register {register} was NOT set to mask {and_mask}|{or_mask}: {result}")
            return False
        else:
            self.log.info(
                f"GW {self.gateway_ip}, TSC {self.get_id()}: Register {register} was NOT set to mask {and_mask}|{or_mask}.")
            return False

    def read_write_device(self) -> None:
        # Incluyo return tras cada elemento para que no haga varias peticiones seguidas a un mismo dispositivo
        # asi va columna a columna y no puede haber swapping por mandar dos peticiones de la misma longitud a un disp
        attempts_wait_time = int(self.config["init_RW"]["attempts_wait_time"])
        max_iterations_per_device = int(self.config["init_RW"]["max_iterations_per_device"])

        if not self.get_finished() and self.iteration < max_iterations_per_device:
            try:
                self.log.info(
                    f"GW {self.gateway_ip}, TSC {self.get_id()}: Starting reading & writing process")
                self.connect()
                self.add_iteration()
                read = True
                written = True
                mask_written = True
                for write_key, value in self.write_dict.items():
                    try:
                        if not pd.isna(value) and (isinstance(value, float) or isinstance(value, int)):
                            if self.set_register(write_key[-5:], value, write_key[5:8]):
                                self.write_dict[write_key] = "OK"
                            else:
                                written = False
                        self.set_written(written)
                        return
                    except Exception as e:
                        self.log.debug(f"GW {self.gateway_ip}, TSC {self.get_id()}: Cannot set register {write_key}={value}: {e}")
                        return
                for mask_write_key, mask in self.mask_write_dict.items():
                    if not pd.isna(mask) and mask != 'OK':
                        and_mask = int(mask[:6], 16)
                        or_mask = int(mask[7:], 16)
                        try:
                            if self.set_mask_register(mask_write_key.replace("Mask_", ""), and_mask, or_mask):
                                self.mask_write_dict[mask_write_key] = "OK"
                            else:
                                mask_written = False
                            self.set_mask_written(mask_written)
                            return
                        except Exception as e:
                            self.log.debug(f"GW {self.gateway_ip}, TSC {self.get_id()}: Cannot set register mask {mask_write_key}={and_mask}|{or_mask}: {e}")
                            return
                for read_key, value in self.read_dict.items():
                    if not isinstance(value, float) or pd.isna(value):
                        self.read_dict[read_key] = self.get_register(read_key[-5:], read_key[4:7])
                        return
                self.set_read(read)

                if written and mask_written and read:
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