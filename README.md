# ECI Election Results Scraper

A robust Python script to scrape constituency-wise election results from the Election Commission of India website.

## Features

✅ **Automatic resumption** - If interrupted, continues from where it stopped  
✅ **Incremental saving** - Saves after each constituency to prevent data loss  
✅ **Error handling** - Continues even if some constituencies fail  
✅ **Detailed logging** - Tracks progress and errors in `eci_scraper.log`  
✅ **Headless mode** - Runs in background without opening browser windows  
✅ **CSV output** - Clean, structured data ready for analysis  

## Prerequisites

1. **Python 3.8+**
2. **Google Chrome** browser installed
3. **ChromeDriver** (will be auto-installed via webdriver-manager)

## Installation

### Step 1: Install Python Dependencies

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install selenium pandas webdriver-manager
```

### Step 2: Verify Chrome Installation

Make sure Google Chrome is installed on your system:
- **Windows**: Chrome should be in Program Files
- **Mac**: Chrome should be in Applications
- **Linux**: Install via `sudo apt install chromium-browser` or `google-chrome-stable`

## Usage

### Basic Usage

Simply run the script:

```bash
python eci_scraper.py
```

This will:
- Scrape all 243 constituencies for Bihar (state code S04)
- Save results to `bihar_election_results.csv`
- Create a log file `eci_scraper.log`
- Take approximately 12-15 minutes (with 3-second delays between requests)

### Customization

Edit the configuration in `eci_scraper.py`:

```python
# Configuration
STATE_CODE = "S04"              # Bihar
TOTAL_CONSTITUENCIES = 243      # Number of constituencies
OUTPUT_FILE = "bihar_election_results.csv"
```

For other states, change the state code:
- Maharashtra: S13
- Jharkhand: S20
- (Check ECI website URLs for other state codes)

### Resume After Interruption

If the script is interrupted (Ctrl+C, crash, etc.), just run it again:

```bash
python eci_scraper.py
```

It will automatically:
- Load previously scraped data
- Skip already completed constituencies
- Continue from where it stopped

## Output Format

The CSV file contains the following columns:

| Column | Description |
|--------|-------------|
| Constituency_Number | Numeric ID (1-243) |
| Constituency_Name | Name of the constituency |
| Serial_No | Candidate serial number |
| Candidate | Candidate name |
| Party | Political party abbreviation |
| EVM_Votes | Votes from EVM |
| Postal_Votes | Postal ballot votes |
| Total_Votes | Total votes received |
| Percentage | Vote percentage |

## Using the Data with Your Local LLM

Once you have the CSV file, you can use it with your local LLM in several ways:

### Option 1: Load Entire CSV (Small Dataset)

```python
import pandas as pd

# Load the data
df = pd.read_csv('bihar_election_results.csv')

# Convert to text for LLM context
context = df.to_string()

# Or convert to JSON
context = df.to_json(orient='records')

# Feed to your LLM
prompt = f"""
Here is the election data:
{context}

Question: Which party won the most seats?
"""
```

### Option 2: Query Specific Data

```python
import pandas as pd

df = pd.read_csv('bihar_election_results.csv')

# Get data for a specific constituency
constituency_data = df[df['Constituency_Name'] == 'PATNA SAHIB']

# Get winner of each constituency
winners = df.loc[df.groupby('Constituency_Number')['Total_Votes'].idxmax()]

# Party-wise seat count
party_seats = winners['Party'].value_counts()
```

### Option 3: Create Summaries

```python
import pandas as pd

df = pd.read_csv('bihar_election_results.csv')

# Create a summary
summary = f"""
Total Constituencies: {df['Constituency_Number'].nunique()}
Total Candidates: {len(df)}
Parties: {', '.join(df['Party'].unique())}

Top 5 Parties by Seats Won:
{winners['Party'].value_counts().head()}
"""

# Feed summary to LLM instead of full data
```

## Troubleshooting

### Chrome/ChromeDriver Issues

**Error**: "chromedriver not found"
```bash
pip install --upgrade webdriver-manager
```

**Error**: "Chrome binary not found"
- Install Google Chrome from https://www.google.com/chrome/
- Or use Chromium: `sudo apt install chromium-browser`

### Selenium Issues

**Error**: "No such element"
- The website structure may have changed
- Check the log file for details
- You may need to update the CSS selectors in the code

### Rate Limiting

If you get blocked:
- Increase delay between requests (change `time.sleep(3)` to `time.sleep(5)`)
- Run during off-peak hours
- Use a VPN if necessary

## Advanced Usage

### Scrape Multiple States

Create a wrapper script:

```python
from eci_scraper import ECIScraper

states = [
    ("S04", 243, "bihar_results.csv"),
    ("S13", 288, "maharashtra_results.csv"),
]

for state_code, total, output_file in states:
    scraper = ECIScraper(state_code, total, output_file)
    scraper.scrape_all()
```

### Export to Database

```python
import sqlite3
import pandas as pd

# Load CSV
df = pd.read_csv('bihar_election_results.csv')

# Save to SQLite
conn = sqlite3.connect('election_results.db')
df.to_sql('results', conn, if_exists='replace', index=False)
conn.close()
```

## Performance

- **Time**: ~12-15 minutes for 243 constituencies (3-second delay)
- **Data Size**: ~100-200 KB for Bihar results
- **Memory**: < 100 MB RAM usage

## Legal & Ethical Considerations

✅ This scraper:
- Uses respectful delays (3 seconds between requests)
- Accesses only public data
- Does not bypass authentication
- Respects robots.txt

⚠️ Remember:
- This is public government data
- Use the data responsibly
- Cite the source (ECI) when publishing analysis
- Don't hammer the server with too many requests

## Support

For issues or questions:
1. Check `eci_scraper.log` for error details
2. Verify your Chrome/ChromeDriver setup
3. Test with a small range first (modify `range(1, 5)` for testing)

## License

This script is provided as-is for educational and research purposes.
