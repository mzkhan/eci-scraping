"""
Bihar 2020 Constituency-Level Data Scraper
Scrapes detailed candidate data for each constituency from IndiaVotes.com
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import pandas as pd
import time
import logging
from datetime import datetime
import os
import re

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('2020/constituency_scraper.log'),
        logging.StreamHandler()
    ]
)

class BiharConstituencyScraper:
    def __init__(self, output_file="2020/bihar_2020_constituencies.csv"):
        self.output_file = output_file
        self.all_data = []

        os.makedirs('2020', exist_ok=True)

        # Setup Chrome options
        self.chrome_options = webdriver.ChromeOptions()
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--disable-gpu')
        self.chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        self.chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)

    def create_driver(self):
        service = Service('/usr/bin/chromedriver')
        driver = webdriver.Chrome(service=service, options=self.chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver

    def get_constituency_links(self, driver, state_url):
        """Extract all constituency links from DataTables_Table_0"""
        logging.info(f"Loading state page: {state_url}")

        driver.get(state_url)
        time.sleep(6)

        # Wait for the table to load
        wait = WebDriverWait(driver, 20)
        table = wait.until(EC.presence_of_element_located((By.ID, "DataTables_Table_0")))

        logging.info("Found DataTables_Table_0")

        # Get all rows
        rows = table.find_elements(By.TAG_NAME, "tr")
        logging.info(f"Total rows in table: {len(rows)}")

        constituencies = []

        # Skip header row(s), process data rows
        for i, row in enumerate(rows[1:], start=1):
            try:
                cells = row.find_elements(By.TAG_NAME, "td")

                if len(cells) >= 2:
                    # First column: constituency number
                    const_num = cells[0].text.strip()

                    # Second column: constituency name with link
                    second_cell = cells[1]
                    link = second_cell.find_element(By.TAG_NAME, "a")
                    const_name = link.text.strip()
                    const_url = link.get_attribute("href")

                    constituencies.append({
                        'number': const_num,
                        'name': const_name,
                        'url': const_url
                    })

                    logging.info(f"Found: {const_num} - {const_name}")

            except Exception as e:
                logging.warning(f"Error processing row {i}: {e}")
                continue

        logging.info(f"Total constituencies found: {len(constituencies)}")
        return constituencies

    def scrape_constituency_details(self, driver, const_num, const_name, const_url):
        """Scrape detailed data for a single constituency"""
        logging.info(f"Scraping: {const_num} - {const_name}")

        try:
            driver.get(const_url)
            time.sleep(5)

            wait = WebDriverWait(driver, 20)

            # Initialize data storage
            const_data = {
                'Constituency_Number': const_num,
                'Constituency_Name': const_name,
                'URL': const_url,
                'Total_Electors': None,
                'Total_Votes_Polled': None,
                'Candidates': []
            }

            # Extract electors and votes polled from the page
            try:
                # Find list items containing the data
                list_items = driver.find_elements(By.TAG_NAME, "li")

                for item in list_items:
                    text = item.text.strip()

                    if 'Electors:' in text and 'Male' not in text and 'Female' not in text:
                        # Extract number after "Electors:"
                        match = re.search(r'Electors:\s*([0-9,]+)', text)
                        if match:
                            const_data['Total_Electors'] = match.group(1).replace(',', '')

                    elif 'Total Votes Polled:' in text:
                        # Extract number and percentage
                        match = re.search(r'Total Votes Polled:\s*([0-9,]+)\s*\(([0-9.]+)%\)', text)
                        if match:
                            const_data['Total_Votes_Polled'] = match.group(1).replace(',', '')
                            const_data['Voter_Turnout_Percent'] = match.group(2)

            except Exception as e:
                logging.warning(f"Could not extract summary data: {e}")

            # Find the results table (id="resultTable")
            try:
                # Wait for the results table to be present
                results_table = wait.until(
                    EC.presence_of_element_located((By.ID, "resultTable"))
                )

                # Find the tbody with candidates
                tbody = results_table.find_element(By.TAG_NAME, "tbody")
                rows = tbody.find_elements(By.TAG_NAME, "tr")

                logging.info(f"Found {len(rows)} candidate rows")

                for row in rows:
                    try:
                        cells = row.find_elements(By.TAG_NAME, "td")

                        if len(cells) >= 6:
                            # Extract candidate data
                            # Structure: #, Position, Name, Votes, Votes %, Party
                            candidate = {
                                'Position': cells[2].text.strip(),  # Position
                                'Candidate_Name': cells[3].text.strip(),  # Name
                                'Votes': cells[4].text.strip().replace(',', ''),  # Votes
                                'Vote_Percentage': cells[5].text.strip().replace('%', ''),  # Votes %
                                'Party': cells[6].text.strip()  # Party (extract link text)
                            }

                            # Try to get party name from link if available
                            try:
                                party_link = cells[6].find_element(By.TAG_NAME, "a")
                                candidate['Party'] = party_link.text.strip()
                            except:
                                pass

                            const_data['Candidates'].append(candidate)

                    except Exception as e:
                        logging.warning(f"Error extracting candidate row: {e}")
                        continue

                logging.info(f"Extracted {len(const_data['Candidates'])} candidates")

            except Exception as e:
                logging.warning(f"Could not find results table: {e}")

            return const_data

        except Exception as e:
            logging.error(f"Error scraping {const_name}: {e}")
            import traceback
            logging.error(traceback.format_exc())
            return None

    def flatten_data_for_csv(self, constituencies_data):
        """Convert nested data to flat CSV format"""
        rows = []

        for const in constituencies_data:
            if not const or not const.get('Candidates'):
                continue

            for candidate in const['Candidates']:
                row = {
                    'Constituency_Number': const['Constituency_Number'],
                    'Constituency_Name': const['Constituency_Name'],
                    'Total_Electors': const.get('Total_Electors', ''),
                    'Total_Votes_Polled': const.get('Total_Votes_Polled', ''),
                }

                # Add all candidate fields
                row.update(candidate)

                rows.append(row)

        return rows

    def run(self, state_url, limit=None, start_from=1):
        """Main scraping workflow"""
        driver = self.create_driver()

        try:
            # Step 1: Get all constituency links
            constituencies = self.get_constituency_links(driver, state_url)

            # Filter by start_from
            constituencies = [c for c in constituencies if int(c['number']) >= start_from]

            # Apply limit if specified
            if limit:
                constituencies = constituencies[:limit]
                logging.info(f"Limiting to {limit} constituencies")

            logging.info(f"Will scrape {len(constituencies)} constituencies")

            # Step 2: Scrape each constituency
            all_const_data = []

            for idx, const in enumerate(constituencies, 1):
                logging.info(f"Progress: {idx}/{len(constituencies)}")

                const_data = self.scrape_constituency_details(
                    driver,
                    const['number'],
                    const['name'],
                    const['url']
                )

                if const_data:
                    all_const_data.append(const_data)

                # Respectful delay
                time.sleep(3)

            # Step 3: Flatten and save to CSV
            if all_const_data:
                flat_data = self.flatten_data_for_csv(all_const_data)

                if flat_data:
                    df = pd.DataFrame(flat_data)
                    df.to_csv(self.output_file, index=False)
                    logging.info(f"Saved {len(flat_data)} candidate records to {self.output_file}")

                    print(f"\n{'='*80}")
                    print(f"SUCCESS! Saved {len(flat_data)} candidate records")
                    print(f"Output file: {self.output_file}")
                    print(f"{'='*80}\n")

                    # Show sample
                    print("Sample data:")
                    print(df.head(10).to_string())
                else:
                    logging.warning("No data to save after flattening")
            else:
                logging.warning("No constituency data collected")

        finally:
            driver.quit()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Scrape Bihar 2020 constituency-level candidate data')
    parser.add_argument('--url',
                        default='https://www.indiavotes.com/vidhan-sabha/2020/bihar-[2000-onwards]/279/58',
                        help='State summary URL')
    parser.add_argument('--limit', type=int, help='Limit number of constituencies (for testing)')
    parser.add_argument('--start-from', type=int, default=1, help='Start from constituency number')
    parser.add_argument('--output', default='2020/bihar_2020_constituencies.csv', help='Output CSV file')

    args = parser.parse_args()

    print("="*80)
    print("Bihar 2020 Constituency-Level Scraper")
    print("="*80)
    print(f"State URL: {args.url}")
    print(f"Output: {args.output}")
    if args.limit:
        print(f"Limit: {args.limit} constituencies")
    print(f"Start from: Constituency {args.start_from}")
    print(f"Log file: 2020/constituency_scraper.log\n")

    scraper = BiharConstituencyScraper(output_file=args.output)

    start_time = datetime.now()
    scraper.run(args.url, limit=args.limit, start_from=args.start_from)

    duration = datetime.now() - start_time
    print(f"\nTotal time: {duration}")
