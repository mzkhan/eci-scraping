"""
ECI Election Results Scraper
Scrapes constituency-wise election results from results.eci.gov.in
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
import time
import logging
from datetime import datetime
import os
import argparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('eci_scraper.log'),
        logging.StreamHandler()
    ]
)

class ECIScraper:
    def __init__(self, state_code="S04", total_constituencies=243, output_file="election_results.csv"):
        """
        Initialize the ECI scraper
        
        Args:
            state_code: State code (S04 for Bihar)
            total_constituencies: Total number of constituencies
            output_file: Output CSV filename
        """
        self.state_code = state_code
        self.total_constituencies = total_constituencies
        self.output_file = output_file
        self.base_url = "https://results.eci.gov.in/ResultAcGenNov2025"
        self.all_data = []
        
        # Setup Chrome options for better performance
        self.chrome_options = webdriver.ChromeOptions()
        self.chrome_options.add_argument('--headless')  # Run in background
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--disable-gpu')
        # Add user agent to appear more like a real browser
        self.chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
    def create_driver(self):
        """Create and return a Chrome driver instance"""
        service = Service('/usr/bin/chromedriver')
        return webdriver.Chrome(service=service, options=self.chrome_options)
    
    def get_completed_constituencies(self):
        """Check which constituencies have already been scraped"""
        completed = set()

        # Check individual constituency files
        output_dir = "constituency_results"
        if os.path.exists(output_dir):
            try:
                files = os.listdir(output_dir)
                for filename in files:
                    if filename.endswith('.csv'):
                        # Extract constituency number from filename (e.g., "001_Name.csv")
                        constituency_num = int(filename.split('_')[0])
                        completed.add(constituency_num)
                logging.info(f"Found {len(completed)} individual constituency files")
            except Exception as e:
                logging.warning(f"Could not read constituency files: {e}")

        # Also check master CSV file
        if os.path.exists(self.output_file):
            try:
                df = pd.read_csv(self.output_file)
                csv_completed = set(df['Constituency_Number'].unique())
                completed.update(csv_completed)
                logging.info(f"Found {len(csv_completed)} constituencies in master CSV")
            except Exception as e:
                logging.warning(f"Could not read existing CSV: {e}")

        if completed:
            logging.info(f"Total {len(completed)} already completed constituencies")

        return completed
    
    def scrape_constituency(self, driver, constituency_num):
        """
        Scrape data for a single constituency
        
        Args:
            driver: Selenium WebDriver instance
            constituency_num: Constituency number
            
        Returns:
            List of dictionaries containing candidate data
        """
        # https://results.eci.gov.in/ResultAcGenNo/v2025/ConstituencywiseS04
        url = f"{self.base_url}/Constituencywise{self.state_code}{constituency_num}.htm"
        logging.info(f"Scraping constituency {constituency_num}: {url}")
        
        try:
            driver.get(url)

            # Wait for page to load completely
            time.sleep(3)  # Initial wait for JavaScript execution

            # Set up wait object with longer timeout
            wait = WebDriverWait(driver, 20)
            
            # Extract constituency name - try multiple selectors
            constituency_name = f"Constituency_{constituency_num}"
            try:
                # Try to find the h2 tag with constituency info
                h2_element = driver.find_element(By.XPATH, "//h2[contains(., 'Assembly Constituency')]")
                if h2_element and h2_element.text.strip():
                    # Extract just the constituency name (e.g., "195 - AGIAON")
                    full_text = h2_element.text.strip()
                    # Parse "Assembly Constituency 195 - AGIAON (Bihar)"
                    if ' - ' in full_text:
                        constituency_name = full_text.split('(')[0].strip().replace('Assembly Constituency', '').strip()
                    else:
                        constituency_name = full_text
                    logging.info(f"Found constituency name: {constituency_name}")
            except NoSuchElementException:
                logging.warning(f"Could not find constituency name, using default: {constituency_name}")
            except Exception as e:
                logging.warning(f"Error extracting constituency name: {e}")
            
            # Find the results table - try multiple approaches
            try:
                # First try to find table with specific class
                table = driver.find_element(By.CSS_SELECTOR, "table.table-striped")
            except NoSuchElementException:
                # Fallback to any table
                table = wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
            
            # Parse table rows
            rows = table.find_elements(By.TAG_NAME, "tr")
            
            if len(rows) <= 1:
                logging.warning(f"No data rows found for constituency {constituency_num}")
                return []
            
            data = []
            headers = []
            
            # Extract headers
            header_row = rows[0]
            header_cells = header_row.find_elements(By.TAG_NAME, "th")
            if not header_cells:
                header_cells = header_row.find_elements(By.TAG_NAME, "td")
            
            headers = [cell.text.strip() for cell in header_cells]
            logging.info(f"Found headers: {headers}")
            
            # Extract data rows
            for row in rows[1:]:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) >= 3:  # At least candidate, party, votes
                    row_data = {
                        'Constituency_Number': constituency_num,
                        'Constituency_Name': constituency_name,
                    }
                    
                    # Map columns - adjust based on actual table structure
                    if len(cols) >= 5:
                        row_data.update({
                            'Serial_No': cols[0].text.strip(),
                            'Candidate': cols[1].text.strip(),
                            'Party': cols[2].text.strip(),
                            'EVM_Votes': cols[3].text.strip(),
                            'Postal_Votes': cols[4].text.strip(),
                            'Total_Votes': cols[5].text.strip() if len(cols) > 5 else '',
                            'Percentage': cols[6].text.strip() if len(cols) > 6 else '',
                        })
                    else:
                        # Simpler structure
                        row_data.update({
                            'Candidate': cols[0].text.strip(),
                            'Party': cols[1].text.strip(),
                            'Votes': cols[2].text.strip(),
                            'Percentage': cols[3].text.strip() if len(cols) > 3 else '',
                        })
                    
                    data.append(row_data)
            
            logging.info(f"Successfully scraped {len(data)} candidates from constituency {constituency_num}")
            return data
            
        except TimeoutException:
            logging.error(f"Timeout loading constituency {constituency_num}")
            return []
        except Exception as e:
            logging.error(f"Error scraping constituency {constituency_num}: {str(e)}")
            return []
    
    def save_data(self):
        """Save collected data to CSV"""
        if self.all_data:
            df = pd.DataFrame(self.all_data)
            df.to_csv(self.output_file, index=False)
            logging.info(f"Saved {len(self.all_data)} records to {self.output_file}")

    def save_constituency_data(self, constituency_data, constituency_num, constituency_name):
        """Save individual constituency data to its own CSV file"""
        if constituency_data:
            # Create output directory if it doesn't exist
            output_dir = "constituency_results"
            os.makedirs(output_dir, exist_ok=True)

            # Create filename with constituency number and name (sanitize name)
            safe_name = constituency_name.replace(" ", "_").replace("/", "-").replace("\\", "-")
            filename = f"{output_dir}/{constituency_num:03d}_{safe_name}.csv"

            df = pd.DataFrame(constituency_data)
            df.to_csv(filename, index=False)
            logging.info(f"Saved {len(constituency_data)} records to {filename}")
            return filename
        return None

    def scrape_all(self, start_from=1):
        """
        Scrape all constituencies
        
        Args:
            start_from: Constituency number to start from (for resuming)
        """
        # Check for already completed constituencies
        completed = self.get_completed_constituencies()
        
        # Load existing data if resuming
        if os.path.exists(self.output_file):
            try:
                df = pd.read_csv(self.output_file)
                self.all_data = df.to_dict('records')
                logging.info(f"Loaded {len(self.all_data)} existing records")
            except Exception as e:
                logging.warning(f"Could not load existing data: {e}")
        
        driver = self.create_driver()
        
        try:
            for constituency_num in range(start_from, self.total_constituencies + 1):
                # Skip if already completed
                if constituency_num in completed:
                    logging.info(f"Skipping constituency {constituency_num} (already completed)")
                    continue
                
                try:
                    # Scrape constituency
                    constituency_data = self.scrape_constituency(driver, constituency_num)

                    if constituency_data:
                        # Save individual constituency file
                        constituency_name = constituency_data[0]['Constituency_Name']
                        self.save_constituency_data(constituency_data, constituency_num, constituency_name)

                        # Add to master data and save combined file
                        self.all_data.extend(constituency_data)
                        self.save_data()

                        logging.info(f"Progress: {constituency_num}/{self.total_constituencies} constituencies completed")

                    # Respectful delay to avoid overloading the server
                    time.sleep(3)
                    
                except Exception as e:
                    logging.error(f"Failed to process constituency {constituency_num}: {e}")
                    # Continue with next constituency
                    continue
            
            logging.info("Scraping completed!")
            logging.info(f"Total records collected: {len(self.all_data)}")

        finally:
            driver.quit()

    def scrape_single(self, constituency_num):
        """
        Scrape data for a single constituency

        Args:
            constituency_num: Constituency number to scrape
        """
        if constituency_num < 1 or constituency_num > self.total_constituencies:
            logging.error(f"Invalid constituency number: {constituency_num}. Must be between 1 and {self.total_constituencies}")
            return False

        logging.info(f"Starting to scrape single constituency: {constituency_num}")

        driver = self.create_driver()

        try:
            # Scrape the constituency
            constituency_data = self.scrape_constituency(driver, constituency_num)

            if constituency_data:
                # Save individual constituency file
                constituency_name = constituency_data[0]['Constituency_Name']
                filename = self.save_constituency_data(constituency_data, constituency_num, constituency_name)

                logging.info(f"Successfully scraped constituency {constituency_num}")
                print(f"\nData saved to: {filename}")
                print(f"Total candidates: {len(constituency_data)}")
                return True
            else:
                logging.warning(f"No data retrieved for constituency {constituency_num}")
                return False

        except Exception as e:
            logging.error(f"Failed to scrape constituency {constituency_num}: {e}")
            return False

        finally:
            driver.quit()

    def generate_summary(self):
        """Generate a summary report of the scraped data"""
        if not self.all_data:
            logging.warning("No data to summarize")
            return
        
        df = pd.DataFrame(self.all_data)
        
        summary = f"""
        ============================================
        SCRAPING SUMMARY
        ============================================
        Total Records: {len(df)}
        Constituencies Scraped: {df['Constituency_Number'].nunique()}
        Total Candidates: {len(df)}
        Unique Parties: {df['Party'].nunique() if 'Party' in df.columns else 'N/A'}
        
        Output File: {self.output_file}
        ============================================
        """
        
        print(summary)
        logging.info(summary)


def main():
    """Main execution function"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='ECI Election Results Scraper - Scrape election data from ECI website',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape all constituencies
  python scraper.py --all

  # Scrape a single constituency
  python scraper.py --constituency 42

  # Scrape all starting from a specific constituency
  python scraper.py --all --start-from 50

  # Use custom state code and total constituencies
  python scraper.py --all --state S05 --total 200
        """
    )

    parser.add_argument('--all', action='store_true',
                        help='Scrape all constituencies')
    parser.add_argument('--constituency', '-c', type=int,
                        help='Scrape a single constituency by number (e.g., 42)')
    parser.add_argument('--start-from', type=int, default=1,
                        help='Start scraping from this constituency number (use with --all)')
    parser.add_argument('--state', default="S04",
                        help='State code (default: S04 for Bihar)')
    parser.add_argument('--total', type=int, default=243,
                        help='Total number of constituencies (default: 243)')
    parser.add_argument('--output', default="bihar_election_results.csv",
                        help='Output CSV filename for combined results (default: bihar_election_results.csv)')

    args = parser.parse_args()

    # Validate arguments
    if not args.all and not args.constituency:
        parser.error("Please specify either --all or --constituency")

    if args.all and args.constituency:
        parser.error("Cannot use --all and --constituency together. Choose one.")

    print("=" * 60)
    print("ECI Election Results Scraper")
    print("=" * 60)

    # Create scraper instance
    scraper = ECIScraper(
        state_code=args.state,
        total_constituencies=args.total,
        output_file=args.output
    )

    start_time = datetime.now()

    try:
        if args.constituency:
            # Scrape single constituency
            print(f"\nScraping constituency: {args.constituency}")
            print(f"State code: {args.state}")
            print(f"Log file: eci_scraper.log\n")

            success = scraper.scrape_single(args.constituency)

            if success:
                print("\n" + "=" * 60)
                print("Scraping completed successfully!")
                print("=" * 60)
            else:
                print("\n" + "=" * 60)
                print("Scraping failed. Check logs for details.")
                print("=" * 60)

        elif args.all:
            # Scrape all constituencies
            print(f"\nStarting to scrape {args.total} constituencies...")
            print(f"Starting from constituency: {args.start_from}")
            print(f"Output file: {args.output}")
            print(f"Log file: eci_scraper.log\n")

            scraper.scrape_all(start_from=args.start_from)
            scraper.generate_summary()

    except KeyboardInterrupt:
        print("\n\nScraping interrupted by user!")
        logging.info("Scraping interrupted by user")
        if args.all:
            scraper.save_data()
            print(f"Progress saved to {args.output}")

    except Exception as e:
        logging.error(f"Fatal error: {e}")
        if args.all:
            scraper.save_data()
            print(f"Error occurred. Progress saved to {args.output}")

    end_time = datetime.now()
    duration = end_time - start_time

    print(f"\nTotal time: {duration}")


if __name__ == "__main__":
    main()
