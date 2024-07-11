import traceback

import PySimpleGUI as sg

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Hockey Pool classes
import browser


def scrape_draft_picks():
    """Scrapes the draft picks data from Fantrax and returns a list of dictionaries."""

    # init driver & draft_picks to None
    driver = None
    draft_picks = []

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

        # for the 2023-2024 draft, there are 2 additional (one-time) rounds for rookies
        original_draft_order = ['Horse Palace 26', 'Shawsome1', 'Camaro SS', 'Witch King', 'WhatA LoadOfIt', 'Banshee', 'High Cheese Chedsie', 'One Man Gang Bang', 'El Paso Pirates', 'Urban Legends', 'Wheels On Meals', "Fowler's Flyers", 'CanDO Know Huang']
        overall_pick = 157
        for draft_round in [13, 14]:
            if draft_round == 14:
                original_draft_order.reverse()
            for round_pick, manager in enumerate(original_draft_order, start=1):
                draft_picks.append({
                    'manager': manager,
                    'draft_round': draft_round,
                    'round_pick': round_pick,
                    'overall_pick': overall_pick,
                })
                overall_pick += 1

        # Create a dictionary to hold pick count for each manager
        pick_count = {}
        # Iterate over draft_picks to add managers_pick_number
        for item in draft_picks:
            manager = item['manager']
            if manager not in pick_count:
                pick_count[manager] = 0
            pick_count[manager] += 1
            item['managers_pick_number'] = pick_count[manager]
            item['drafted_player'] = ''

    except Exception as e:
        sg.popup_error(f"An exception occurred in scrape_draft_picks(): {e}\n{traceback.format_exc()}")

    finally:
        # Delete the driver object
        del driver

    return draft_picks
