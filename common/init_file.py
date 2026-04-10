import os
import shutil
from datetime import datetime

import configparser
from common import common


class InitFile():
    def __init__(self):
        self.file_path = os.path.join(common.CONFIG_DIR, "init_FW.ini")
        self.defaults = {
            "fw_update": "1",
            "mac_files": "1",
            "loop_time": "300",
            "gw_port": "502",
            "vcc_top_threshold": "36000",
            "vcc_bottom_threshold": "28000",
            "maximum_threads": "100",
            "threads_per_gateway": "1",
            "max_attempts": "1",
            "max_equal_addr_attempts": "1",
            "max_update_attempts": "1",
            "max_verify_attempts": "1",
            "attempts_wait_time": "1",
            "connection_timeout": "3",
            "equal_addr_attempts_wait_time": "1",
            "max_iterations": "65000",
            "max_iterations_per_device": "1000"
        }

    def create(self):
        if not os.path.exists(self.file_path):
            config = configparser.ConfigParser()
            config.add_section("init_FW")
            for key, value in self.defaults.items():
                config.set("init_FW", key, value)

            with open(self.file_path, "w") as config_file:
                config.write(config_file)
                config_file.close()

    def load(self) -> None:
        if not os.path.exists(self.file_path):
            self.create()
        config_file = configparser.ConfigParser(self.defaults)
        config_file.read(self.file_path)
        return config_file

        return False

    def copy(self, file_name: str) -> None:
        copy_folder = os.path.join(self.file_path, "Hist_Init_FW")
        if not os.path.exists(copy_folder):
            os.mkdir(copy_folder)

        date = datetime.now().strftime("%Y,%m,%d-%H%M")
        shutil.copy(os.path.join(
            copy_folder, date + "_init_FW.txt"))


if __name__ == "__main__":
    init_file = InitFile()
    config = init_file.load()
    print(config.get("init_FW", "STI_Group_s214"))
