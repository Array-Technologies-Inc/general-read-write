import pandas as pd
import os
import tempfile
import shutil
import glob
from datetime import datetime
from common import common
from device.gateway import Gateway


class Reporting:
    def __init__(self, id_snc: int) -> None:
        self.id_snc = id_snc
        self.start_time = datetime.now()
        self.end_time = None
        self.gateway_list = {}

    def add_gateway(self, gateway: Gateway) -> None:
        self.gateway_list[gateway.get_ip()] = gateway

    def set_end_time(self, time: datetime) -> None:
        self.end_time = time

    def write_header(self, report_file):
        full_devices = 0
        read_devices = 0
        written_devices = 0
        aborted_devices = 0
        num_devices = 0
        percent_total = 0
        report_mac_summary = ""
        
        for gw in self.gateway_list.values():
            full_devices += gw.get_full_tsc() + gw.get_full_iwc()
            read_devices += gw.get_read_tsc() + gw.get_read_iwc()
            written_devices += gw.get_written_tsc() + gw.get_written_iwc()
            aborted_devices += gw.get_aborted_tsc() + gw.get_aborted_iwc()
            num_devices += gw.get_tsc_num() + gw.get_iwc_num()
            #tengo los gws añadidos, tengo una variable que es si está la mac actualizada, lo añado como parte de la cabecera

        report_file.write(report_mac_summary)

        if num_devices > 0:
            percent_total = (full_devices * 100.0) / (num_devices)

        report_header = "Summary Table\t ==> Read {full_devices}/{total_devices} = {percent_total:6.2f} % \tAborted: {aborted_devices:3}\n\n".format(  # noqa: E501
            full_devices=full_devices,
            total_devices=num_devices,
            percent_total=percent_total,
            aborted_devices=aborted_devices
        )
        report_file.write(report_header)

        report_file.write("\n")
        for gw in self.gateway_list.values():
            gw_tsc_percent = 0
            gw_iwc_percent = 0
            if gw.get_tsc_num() != 0:
                gw_tsc_percent = (100 * gw.get_full_tsc()) / gw.get_tsc_num()
            if gw.get_iwc_num() != 0:
                gw_iwc_percent = (100 * gw.get_full_iwc()) / gw.get_iwc_num()
            report_gateway_resume = "GW {} ==> TSC W{:3}|R{:3} -> F{:3}/T{:3} = {:6.2f}%\t IWC W{:3}|R{:3} -> F{:3}/T{:3} = {:6.2f}%\t Aborted: TSC={:3} IWC={:3}\n".format(  # noqa: E501
                gw.get_ip(),
                gw.get_written_tsc(),
                gw.get_read_tsc(),
                gw.get_full_tsc(),
                gw.get_tsc_num(),
                gw_tsc_percent,
                gw.get_written_iwc(),
                gw.get_read_iwc(),
                gw.get_full_iwc(),
                gw.get_iwc_num(),
                gw_iwc_percent,
                gw.get_aborted_tsc(),
                gw.get_aborted_iwc())
            report_file.write(report_gateway_resume)
        report_file.write("\n")
        report_file.write("Start Time: {}\n".format(
            self.start_time.strftime("%d/%m/%Y - %H:%M:%S")))
        if self.end_time is not None:
            report_file.write("End Time: {}\n".format(
                self.end_time.strftime("%d/%m/%Y - %H:%M:%S")))

        #report_file.write("\n")
        #report_columns = "TSC/IWC\tProdIdInit.\tProdIdFin.\tGW\tConnect.\tInit.\tPercent\tFull\tCS_sent/recv\tApto.\tBoolL\tFin.\tReadErrors\tSendErrors\tTSCLocalDate\\Hour\tTSCUtcDate/Hour\t\tDuration\n"  # noqa: E501
        #report_file.write(report_columns)

    def rotate_files(self):
        max_files = 6
        list_of_files = glob.glob(os.path.join(common.LOG_DIR, "*_FW_updater.txt"))
        list_of_files.sort(key=os.path.getmtime)

        delete = len(list_of_files) - max_files
        for x in range(0, delete):
            os.remove(list_of_files[x])

    def generate_report(self, device_file, device_file_table):

        self.rotate_files()

        with open(os.path.join(
            common.LOG_DIR, self.start_time.strftime(
                "%Y%m%d_%H%M") + "_" + self.id_snc + "_FW_updater.txt"), "w") as report:
            self.write_header(report)
            report.close()

            for gw in self.gateway_list.values():

                for device in list(gw.get_tsc_list().values()) + list(gw.get_iwc_list().values()):
                    try:
                        for read_req, value in device.read_dict.items():
                            if not pd.isna(value): device_file_table.loc[device_file_table["TCU"] == device.name, read_req] = value
                        for write_req, value in device.write_dict.items():
                            device_file_table[write_req] = device_file_table[write_req].astype(str)
                            if not pd.isna(value): device_file_table.loc[device_file_table["TCU"] == device.name, write_req] = str(value)
                        device_file_table.loc[device_file_table["TCU"] == device.name, "Attempts"] = device.get_iteration() if device.get_iteration() else 0

                    except Exception as e:
                        print(f"Error updating device table: {e}")

        try:
            device_table_str = device_file_table.astype(str)

            dir_name = os.path.dirname(device_file)
            ext = os.path.splitext(device_file)[1]  # ".xlsx"

            with tempfile.NamedTemporaryFile(delete=False, dir=dir_name, suffix=ext) as tmp:
                temp_name = tmp.name

            try:
                with pd.ExcelWriter(temp_name, engine="openpyxl", mode="w") as writer:
                    device_table_str.to_excel(writer, sheet_name="Devices", index=False)
                os.replace(temp_name, device_file)
            finally:
                if os.path.exists(temp_name):
                    try:
                        os.remove(temp_name)
                    except:
                        pass

        except Exception as e:
            print(f"{device_file} cannot be written: {e}")    
        
        return device_file_table
