# README.md

## Directory Structure
```
US100-Stock-Dashboard/
│-- Data Fetcher.py
│-- Interactive Dashboard.py
│-- Equal Weighted_Index Composition.py
│-- constant.py
│-- requirements.txt
│-- Database.zip
│-- sample_output/
│-- README.md
```

## Installation & Setup
1. **Clone Repository**:
   ```sh
   git clone https://github.com/g-st180/US100-Stock-Dashboard
   cd US100-Stock-Dashboard
   ```
2. **Install Dependencies**:
   ```sh
   pip install -r requirements.txt
   ```
3. **Extract Database**:
   - Unzip `Database.zip` and place it in the correct path as referenced in the scripts.

## How to Run
### 1. Fetch Data & Store in Database
```sh
python Data Fetcher.py
```
This script retrieves market data for the past 5 years and stores it in a DuckDB database.

### 2. Generate Index Composition
```sh
python Equal Weighted_Index Composition.py
```
This script processes market data, identifies top 100 companies daily, calculates index performance, and tracks composition changes.

### 3. Run Interactive Dashboard
```sh
python Interactive Dashboard.py
```
This launches a web-based dashboard displaying index performance and composition changes.

## Assumptions
- Data fetched is assumed to be accurate as provided by Yahoo Finance.
- A company listed in the S&P 500 may not necessarily be in the top 100 U.S. companies by market cap.

## Project Flow
1. **Fetch stock market data**: The script retrieves historical stock prices and market capitalization data from Yahoo Finance.
2. **Store data in DuckDB**: The collected data is stored in a structured DuckDB database to enable efficient querying.
3. **Compute equal-weighted index**: Each of the top 100 companies is assigned an equal weight, and the overall index performance is calculated.
4. **Track index composition changes**: Daily shifts in the composition of the top 100 companies are logged.
5. **Generate reports and dashboards**: The data is visualized through an interactive dashboard with time-series analysis, company weights, and index trends.

![Dashboard](https://github.com/user-attachments/assets/5f458e70-2710-4cda-b542-27765f3cf083)

