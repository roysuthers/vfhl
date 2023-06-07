import os
import sys
import traceback
from selenium.webdriver import Firefox
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.firefox.options import Options

def setBrowserOptions():

    try:
        opts = Options()
        opts.headless = True
        opts.profile = 'C:/Users/Roy/AppData/Roaming/Mozilla/Firefox/Profiles/wafmugwl.Fantrax'
        geckodriver_path = os.path.join(os.getcwd(), 'geckodriver.exe')
        driver = Firefox(executable_path=geckodriver_path, options=opts)

    except Exception as e:
        print(f'{traceback.format_exception(type(e))} in setBrowserOptions()')
        return None

    return driver
