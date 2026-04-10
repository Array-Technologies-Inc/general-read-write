import pandas as pd
import os
import tempfile
import shutil
import glob
from datetime import datetime
from common import common
from device.gateway import Gateway


class Reporting:
    def __init__(self, id_snc: int, tsc_version: int, iwc_version: int) -> None:
        self.id_snc = id_snc
        self.tsc_version = tsc_version
        self.iwc_version = iwc_version
        self.start_time = datetime.now()
        self.end_time = None
        self.gateway_list = {}

    def add_gateway(self, gateway: Gateway) -> None:
        self.gateway_list[gateway.get_ip()] = gateway

    def set_end_time(self, time: datetime) -> None:
        self.end_time = time

    def write_header(self, report_file):
        full_devices = 0
        aborted_devices = 0
        num_devices = 0
        percent_total = 0
        report_mac_summary = ""
        
        for gw in self.gateway_list.values():
            full_devices += gw.get_full_tsc() + gw.get_full_iwc()
            aborted_devices += gw.get_aborted_tsc() + gw.get_aborted_iwc()
            num_devices += gw.get_tsc_num() + gw.get_iwc_num()
            #tengo los gws añadidos, tengo una variable que es si está la mac actualizada, lo añado como parte de la cabecera

        report_file.write(report_mac_summary)

        if num_devices > 0:
            percent_total = (full_devices * 100.0) / (num_devices)

        report_header = "Summary Table\t ==> FW updated {full_devices}/{total_devices} = {percent_total:6.2f} % \tAborted: {aborted_devices:3}\n\n".format(  # noqa: E501
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
            report_gateway_resume = "GW {} ==> MACs updated: {}    TSC v{}: {:3}/{:3} = {:6.2f}%     IWC v{}: {:3}/{:3} = {:6.2f}%\t Aborted: TSC={:3} IWC={:3}\n".format(  # noqa: E501
                gw.get_ip(),
                gw.get_mac_file_updated(),
                self.tsc_version,
                gw.get_full_tsc(),
                gw.get_tsc_num(),
                gw_tsc_percent,
                self.iwc_version,
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
                        if "ProductId Init" not in device_file_table:
                            device_file_table["ProductId Init"] = '0'
                        if "ProductId End" not in device_file_table:
                            device_file_table["ProductId End"] = '0'
                        device_file_table["ProductId Init"] = device_file_table["ProductId Init"].astype(str)
                        device_file_table["ProductId End"] = device_file_table["ProductId End"].astype(str)
                        device_file_table.loc[device_file_table["TCU"] == device.name, "ProductId Init"] = device.get_prod_id_init() if device.get_prod_id_init() else '0'
                        device_file_table.loc[device_file_table["TCU"] == device.name, "ProductId Sent"] = device.get_prod_id_sent() if device.get_prod_id_sent() else '0'
                        device_file_table.loc[device_file_table["TCU"] == device.name, "ProductId End"] = device.get_prod_id_end() if device.get_prod_id_end() else '0'
                        device_file_table.loc[device_file_table["TCU"] == device.name, "Connected"] = "Yes" if device.get_comm_status() else 'No'
                        device_file_table.loc[device_file_table["TCU"] == device.name, "Percentage"] = device.get_percent() if device.get_percent() else 0
                        device_file_table.loc[device_file_table["TCU"] == device.name, "Checksum sent"] = device.get_cs_sent() if device.get_cs_sent() else 0
                        device_file_table.loc[device_file_table["TCU"] == device.name, "Checksum recv"] = device.get_cs_received() if device.get_cs_received() else 0
                        device_file_table.loc[device_file_table["TCU"] == device.name, "Bootloader"] = "Yes" if device.get_bootloaded() else 'No'
                        device_file_table.loc[device_file_table["TCU"] == device.name, "Ended"] = "Yes" if device.get_finished() else "No"
                        device_file_table.loc[device_file_table["TCU"] == device.name, "Read errors"] = device.get_read_errors() if device.get_read_errors() else 0
                        device_file_table.loc[device_file_table["TCU"] == device.name, "Send errors"] = device.get_sent_errors() if device.get_sent_errors() else 0
                        device_file_table.loc[device_file_table["TCU"] == device.name, "TSC local date"] = device.get_local_date() if device.get_local_date() else "---"
                        device_file_table.loc[device_file_table["TCU"] == device.name, "TSC UTC date"] = device.get_local_date_utc() if device.get_local_date_utc() else "---"
                        device_file_table.loc[device_file_table["TCU"] == device.name, "Duration"] = device.get_duration() if device.get_local_date_utc() else "---"
                    except Exception as e:
                        print(f"Error updating device table: {e}")

                    status = "{tsc_id}\t{product_id_init}\t\t{product_id_end}\t\t{gateway}\t{comm_status}\t\t".format(  # noqa: E501
                        tsc_id=device.get_id(),
                        product_id_init=device.get_prod_id_init(),
                        product_id_end=device.get_prod_id_end(),
                        gateway=device.get_gateway_ip(),
                        comm_status="Yes" if device.get_comm_status() else 'No'
                    )

                    progress = "{init}\t{percent_sent:.2f}%\t{full}\t".format(
                        init="Yes" if device.get_start() else "No",
                        percent_sent=device.get_percent(),
                        full="Yes" if device.get_full() else "No"
                    )

                    validate = "{cs_sent}/{cs_received}\t\t{apto}\t{bootloader}\t{fin}\t".format(  # noqa: E501
                        cs_sent=device.get_cs_sent(),
                        cs_received=device.get_cs_received(),
                        apto="OK" if device.get_apto() else "NOK",
                        bootloader="Yes" if device.get_bootloaded() else "No",
                        fin="Yes" if device.get_finished() else "---"
                    )

                    errors = "{read_errors}\t\t{sent_errors}\t\t".format(
                        read_errors=device.get_read_errors(),
                        sent_errors=device.get_sent_errors()
                    )

                    date = "{local_date}\t{tsc_date}\t{duration}\t".format(
                        local_date=device.get_local_date(),
                        tsc_date=device.get_local_date_utc(),
                        duration=device.get_duration()
                    )

                    #report.write(
                    #    status + progress + validate + errors + date + "\n"
                    #)

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

            #if os.path.exists(device_file):
            #    os.remove(device_file)  # Borra el archivo si ya existe
            #time.sleep(5)
            # Save the excel sheet
            # with pd.ExcelWriter(device_file, engine="openpyxl", mode="w") as writer:
            #     device_table_str.to_excel(writer, sheet_name="Devices", index=False)
        except Exception as e:
            print(f"{device_file} cannot be written: {e}")    
        
        return device_file_table
