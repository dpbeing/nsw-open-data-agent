Great. Next, let’s document what you’ve built so someone reviewing your project can understand and run it. In IntelliJ, open the root `README.md` and use this as a first draft:

```markdown
# NSW Rental Bond Insights Agent

A local AI agent that answers questions about NSW rental bond lodgements using
constrained, read-only DuckDB tools. It processes the source workbook with
PySpark, stores the prepared data in Parquet and DuckDB, and presents answers
in a Streamlit chat app.

## Architecture

Excel workbook → PySpark preparation → Parquet and DuckDB → Python query tools
→ Ollama (Qwen3 8B) → Streamlit

The model selects from predefined query tools. It does not generate arbitrary
SQL to run against the database.

## Data source and limitations

Source: [NSW Rental Bond Lodgement dataset](https://data.nsw.gov.au/data/dataset/rental-bond-lodgement), published by NSW Fair Trading.

The project uses the 2025 annual workbook. Rental bond data is supplied at the
start of a tenancy and may indicate recent rent values; it does not represent
all current rental listings or asking rents. See the source for its licence
and attribution details.

## Data preparation

The pipeline processed 322,307 records for 2025. Its quality summary identified:

- 3,821 records with unknown rent
- 54 records with zero or negative rent
- 36 records with unmapped dwelling type codes

Rent queries exclude unknown, zero and negative rent values. The app shows the
filters and supporting query evidence with its answers.

## Run locally

Requirements: Python 3.12, Java 21, `uv`, and [Ollama](https://ollama.com/).

1. Download the 2025 workbook from the source dataset and save it as:

   `data/raw/rental_bonds_2025.xlsx`

2. Install project dependencies:

   ```bash
   uv sync
   ```

3. Prepare the data:

   ```bash
   uv run python src/nsw_open_data_agent/pipeline/prepare_data.py
   ```

4. Start the app:

   ```bash
   uv run streamlit run src/nsw_open_data_agent/app.py
   ```

The app uses the locally installed `qwen3:8b` Ollama model and the generated
DuckDB database under `data/processed/`.

## Example questions

- What is the median rent for a 4-bedroom flat in postcode 2000?
- Which postcodes have the highest median rent for 2-bedroom units?

## Tech stack

Python · PySpark · Parquet · DuckDB · Ollama · Qwen3 · Streamlit
```

The source description says these are bond lodgements reported by postcode and supplied at the beginning of a tenancy, so the README makes that limitation clear. 

Save it and check IntelliJ’s Markdown preview. If one of the commands doesn’t match your moved file paths, paste the error and we’ll adjust it.