"""
Test script to debug page loading issues
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time

# Setup Chrome options
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-gpu')

# Add user agent to look more like a real browser
chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

# Create driver
service = Service('/usr/bin/chromedriver')
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    url = "https://results.eci.gov.in/ResultAcGenNov2025/ConstituencywiseS04195.htm"
    print(f"Loading: {url}")

    driver.get(url)

    # Wait a bit for page to load
    time.sleep(5)

    # Get page source
    page_source = driver.page_source

    # Save to file for inspection
    with open('/tmp/page_source.html', 'w', encoding='utf-8') as f:
        f.write(page_source)

    print(f"\nPage title: {driver.title}")
    print(f"Page source length: {len(page_source)} characters")
    print(f"\nFirst 500 characters of page:")
    print(page_source[:500])

    # Try to find tables
    tables = driver.find_elements(By.TAG_NAME, "table")
    print(f"\nNumber of tables found: {len(tables)}")

    if tables:
        for i, table in enumerate(tables):
            rows = table.find_elements(By.TAG_NAME, "tr")
            print(f"Table {i+1}: {len(rows)} rows")

    # Check for common error indicators
    if "access denied" in page_source.lower():
        print("\n⚠️  WARNING: Page contains 'Access Denied' message!")
    if "403" in page_source:
        print("\n⚠️  WARNING: Page contains '403' error!")
    if "forbidden" in page_source.lower():
        print("\n⚠️  WARNING: Page contains 'Forbidden' message!")

    print(f"\nFull page source saved to: /tmp/page_source.html")

finally:
    driver.quit()
