"""
ECI Election Results Scraper
Scrapes constituency-wise election results from results.eci.gov.in
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
import time
import logging
from datetime import datetime
import os

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
        
    def create_driver(self):
        """Create and return a Chrome driver instance"""
        return webdriver.Chrome(options=self.chrome_options)
    
    def get_completed_constituencies(self):
        """Check which constituencies have already been scraped"""
        if os.path.exists(self.output_file):
            try:
                df = pd.read_csv(self.output_file)
                completed = set(df['Constituency_Number'].unique())
                logging.info(f"Found {len(completed)} already completed constituencies")
                return completed
            except Exception as e:
                logging.warning(f"Could not read existing CSV: {e}")
                return set()
        return set()
    
    def scrape_constituency(self, driver, constituency_num):
        """
        Scrape data for a single constituency
        
        Args:
            driver: Selenium WebDriver instance
            constituency_num: Constituency number
            
        Returns:
            List of dictionaries containing candidate data
        """
        url = f"{self.base_url}/candidateswise-{self.state_code}{constituency_num:03d}.htm"
        logging.info(f"Scraping constituency {constituency_num}: {url}")
        
        try:
            driver.get(url)
            
            # Wait for page to load
            wait = WebDriverWait(driver, 15)
            
            # Try to find the main content
            time.sleep(2)  # Additional wait for dynamic content
            
            # Extract constituency name - try multiple selectors
            constituency_name = f"Constituency_{constituency_num}"
            try:
                # Try different possible selectors for constituency name
                name_selectors = [
                    (By.CLASS_NAME, "constName"),
                    (By.TAG_NAME, "h2"),
                    (By.TAG_NAME, "h3"),
                    (By.XPATH, "//div[contains(@class, 'constituency')]"),
                ]
                
                for selector_type, selector_value in name_selectors:
                    try:
                        element = driver.find_element(selector_type, selector_value)
                        if element.text.strip():
                            constituency_name = element.text.strip()
                            break
                    except NoSuchElementException:
                        continue
                        
            except Exception as e:
                logging.warning(f"Could not find constituency name: {e}")
            
            # Find the results table
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
                        self.all_data.extend(constituency_data)
                        
                        # Save after each constituency (incremental save)
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
    print("=" * 60)
    print("ECI Election Results Scraper")
    print("=" * 60)
    
    # Configuration
    STATE_CODE = "S04"  # Bihar
    TOTAL_CONSTITUENCIES = 243
    OUTPUT_FILE = "bihar_election_results.csv"
    
    # Create scraper instance
    scraper = ECIScraper(
        state_code=STATE_CODE,
        total_constituencies=TOTAL_CONSTITUENCIES,
        output_file=OUTPUT_FILE
    )
    
    # Start scraping
    print(f"\nStarting to scrape {TOTAL_CONSTITUENCIES} constituencies...")
    print(f"Output file: {OUTPUT_FILE}")
    print(f"Log file: eci_scraper.log\n")
    
    start_time = datetime.now()
    
    try:
        scraper.scrape_all(start_from=1)
        scraper.generate_summary()
        
    except KeyboardInterrupt:
        print("\n\nScraping interrupted by user!")
        logging.info("Scraping interrupted by user")
        scraper.save_data()
        print(f"Progress saved to {OUTPUT_FILE}")
    
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        scraper.save_data()
        print(f"Error occurred. Progress saved to {OUTPUT_FILE}")
    
    end_time = datetime.now()
    duration = end_time - start_time
    
    print(f"\nTotal time: {duration}")
    print(f"Data saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
