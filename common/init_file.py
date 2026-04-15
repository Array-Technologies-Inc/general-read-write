import os
import shutil
from datetime import datetime

import configparser
from common import common


class InitFile():
    def __init__(self):
        self.file_path = os.path.join(common.CONFIG_DIR, "init_RW.ini")
        self.defaults = {
            "tsc_enable": "1",
            "iwc_enable": "0",
            "loop_time": "300",
            "gw_port": "502",
            "maximum_threads": "100",
            "threads_per_gateway": "1",
            "attempts_wait_time": "1",
            "connection_timeout": "3",
            "max_iterations_per_device": "1000"
        }

    def create(self):
        if not os.path.exists(self.file_path):
            config = configparser.ConfigParser()
            config.add_section("init_RW")
            for key, value in self.defaults.items():
                config.set("init_RW", key, value)

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
        copy_folder = os.path.join(self.file_path, "Hist_Init_RW")
        if not os.path.exists(copy_folder):
            os.mkdir(copy_folder)

        date = datetime.now().strftime("%Y,%m,%d-%H%M")
        shutil.copy(os.path.join(
            copy_folder, date + "_init_RW.txt"))


if __name__ == "__main__":
    init_file = InitFile()
    config = init_file.load()
    print(config.get("init_RW", "STI_Group_s214"))
