import traceback

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Hockey Pool classes
import browser


def scrape_draft_picks():
    """Scrapes the draft picks data from Fantrax and returns a list of dictionaries."""

    try:

        driver = browser.setBrowserOptions()

        # Set default wait time
        wait = WebDriverWait(driver, 60)

        driver.get('https://www.fantrax.com/newui/fantasy/draftPicks.go?leagueId=fcchh3fklgl33mrk&season=2023&viewType=ROUND')

        # Find all the draft results tables
        draft_results_tables = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'draftResultsTable')))

        # Create a list of dictionaries for each draft pick
        draft_picks = [
            {
                 "manager": draft_pick_data.find_elements(By.TAG_NAME, "td")[0].text,
                "draft_round": i + 1,
                "round_pick": int(draft_pick_data.find_elements(By.TAG_NAME, "td")[1].text),
                "overall_pick": int(draft_pick_data.find_elements(By.TAG_NAME, "td")[2].text),
            }
            for i, table in enumerate(draft_results_tables)
            for draft_pick_data in table.find_elements(By.TAG_NAME, "tr")[1:]  # Skip the first row with column headings
        ]

    except Exception as e:
        print(f"An exception occurred in scrape_draft_picks(): {e}\n{traceback.format_exc()}")

    finally:
        # Delete the driver object
        del driver

    return draft_picks
