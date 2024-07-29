import os
import psutil
import sys
import threading
import traceback
from pathlib import Path
from selenium.webdriver import Firefox
# from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.firefox.options import Options

import PySimpleGUI as sg

class Browser:

    def __init__(self, browser_download_dir=''):

        self.browser_download_dir = browser_download_dir
        # self.browser = self.setBrowserOptions()
        self.browser = None
        self.firefox_pids = []

        return

    def __enter__(self):

        # Create a separate thread to initialize the browser
        thread = threading.Thread(target=self.init_browser)
        thread.start()
        thread.join(timeout=60)  # Set timeout

        if thread.is_alive():
            self.terminate_orphaned_processes()
            raise Exception("Initialization is taking longer than expected...")
        else:
            return self.browser

    def init_browser(self):
        self.browser = self.setBrowserOptions()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            self.browser.quit()
        self.terminate_orphaned_processes()

        return

    def setBrowserOptions(self):

        # Constants
        PROFILE_PATH = Path('C:/Users/Roy/AppData/Roaming/Mozilla/Firefox/Profiles/wafmugwl.Fantrax')
        DRIVER_NAME = 'geckodriver.exe'

        try:
            options = Options()
            options.headless = True
            options.profile = str(PROFILE_PATH)

            if self.browser_download_dir != '':
                options.set_preference("browser.download.folderList", 2)
                options.set_preference("browser.download.manager.showWhenStarting", False)
                options.set_preference("browser.download.dir", self.browser_download_dir)
                options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/octet-stream")

            driver_path  = Path(os.getcwd()) / DRIVER_NAME
            self.browser = Firefox(executable_path=str(driver_path) , options=options)

            self.browser.set_page_load_timeout(30)  # Set timeout to 10 seconds

            # Track the PIDs of the Firefox processes
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] == 'firefox.exe':
                    self.firefox_pids.append(proc.info['pid'])

        except FileNotFoundError:
            raise Exception(f"Driver not found: {driver_path}")
            return None

        except Exception as e:
            sg.popup_error(f'Error in {sys._getframe().f_code.co_name}: {e}')
            return None

        return self.browser

    def terminate_orphaned_processes(self):
        for pid in self.firefox_pids:
            try:
                proc = psutil.Process(pid)
                proc.terminate()
            except psutil.NoSuchProcess:
                pass