import traceback

from selenium.common.exceptions import NoSuchElementException, TimeoutException
# from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.support.expected_conditions import _find_element
from selenium.webdriver.support.ui import Select, WebDriverWait

# Hockey Pool classes
import browser


def scrape_draft_picks():

    try:

        driver = browser.setBrowserOptions()

        # Set default wait time
        wait = WebDriverWait(driver, 60)

        driver.get('https://www.fantrax.com/newui/fantasy/draftPicks.go?leagueId=fcchh3fklgl33mrk&season=2023&viewType=ROUND')

        tables = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'draftResultsTable')))

        draft_picks = []
        for i, table in enumerate(tables):
            # skip first row that is for the table column headings
            rows = table.find_elements(By.TAG_NAME, 'tr')[1:]
            for row in rows:
                data = row.find_elements(By.TAG_NAME, 'td')
                manager = data[0].text
                draft_round = i + 1
                round_pick = int(data[1].text)
                overall_pick = int(data[2].text)
                draft_picks.append({'manager': manager, 'draft_round': draft_round, 'round_pick': round_pick, 'overall_pick': overall_pick})

    except Exception as e:
        print(f'{traceback.format_exception(type(e))} in scrape_draft_picks()')
        del driver

    return draft_picks
