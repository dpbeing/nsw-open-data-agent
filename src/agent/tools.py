from pathlib import Path
import duckdb

MODEL = "qwen3:8b"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE = PROJECT_ROOT / "data" / "processed" / "rental_bonds.duckdb"
# DATABASE = (
#         Path(__file__).resolve().parent / "data" / "processed" / "rental_bonds.duckdb"
# )

SYSTEM_PROMPT = """
You answer questions using NSW Fair Trading rental bond lodgements for 2025.

You have two tool: rank_median_rents and also by postcodes.
Use it for questions comparing median weekly rent by postcode.
The tool accepts a dwelling type code:
F = flat/unit, H = house, T = terrace/townhouse/semi-detached,
O = other.
When the question names one postcode, use median_rent_for_postcode.
When it asks to rank postcodes, use rank_median_rents.
The dataset measures bedrooms, not total rooms. If you interpret “rooms”
as bedrooms, say so in the answer.

Use only the tool result for factual rent figures. Explain the filters,
sample size, and that bond lodgements are not all current rental contracts.
If the question cannot be answered with this tool, say so.
Be concise.
"""


def rank_median_rents(dwelling_type: str, bedrooms: int) -> dict:
    """Rank postcodes by 2025 median weekly rent for a dwelling type and bedroom count.

    dwelling_type: F (flat/unit), H (house), T (terrace/townhouse), or O (other).
    bedrooms: Number of bedrooms; 0 can mean a studio or bedsitter.
    """
    code = dwelling_type.strip().upper()
    aliases = {
        "FLAT": "F",
        "FLATS": "F",
        "UNIT": "F",
        "UNITS": "F",
        "FLAT/UNIT": "F",
        "HOUSE": "H",
        "HOUSES": "H",
        "TERRACE": "T",
        "TOWNHOUSE": "T",
        "OTHER": "O",
    }
    code = aliases.get(code, code)

    if code not in {"F", "H", "T", "O"}:
        return {"error": "Choose F, H, T, or O for dwelling type."}

    if not isinstance(bedrooms, int) or not 0 <= bedrooms <= 20:
        return {"error": "Bedrooms must be a whole number from 0 to 20."}

    connection = duckdb.connect(str(DATABASE), read_only=True)
    try:
        rows = connection.execute(
            """
            SELECT
                postcode,
                COUNT(*) AS lodgements,
                ROUND(MEDIAN(weekly_rent), 2) AS median_weekly_rent
            FROM rental_bonds
            WHERE dwelling_type = ?
              AND bedrooms = ?
              AND rent_status = 'valid'
            GROUP BY postcode
            HAVING COUNT(*) >= 10
            ORDER BY median_weekly_rent DESC
                LIMIT 10
            """,
            [code, bedrooms],
        ).fetchall()
    finally:
        connection.close()

    return {
        "source": "NSW Fair Trading rental bond lodgements, 2025",
        "metric": "median weekly rent in AUD",
        "filters": {"dwelling_type": code, "bedrooms": bedrooms},
        "exclusions": "Unknown and non-positive rents; postcode groups with fewer than 10 lodgements",
        "results": [
            {
                "postcode": str(postcode),
                "lodgements": int(lodgements),
                "median_weekly_rent": float(median),
            }
            for postcode, lodgements, median in rows
        ],
    }


def median_rent_for_postcode(
        postcode: str,
        dwelling_type: str,
        bedrooms: int,
) -> dict:
    """Get the 2025 median weekly rent for one postcode, type, and bedroom count."""
    postcode = str(postcode).strip()

    if not postcode.isdigit() or len(postcode) > 4:
        return {"error": "Enter a valid four-digit postcode."}
    postcode = postcode.zfill(4)

    code = dwelling_type.strip().upper()
    aliases = {
        "HOUSE": "H",
        "HOUSES": "H",
        "FLAT": "F",
        "UNIT": "F",
        "TERRACE": "T",
        "TOWNHOUSE": "T",
        "OTHER": "O",
    }
    code = aliases.get(code, code)

    if code not in {"F", "H", "T", "O"}:
        return {"error": "Choose F, H, T, or O for dwelling type."}
    if not isinstance(bedrooms, int) or not 0 <= bedrooms <= 20:
        return {"error": "Bedrooms must be a whole number from 0 to 20."}

    connection = duckdb.connect(str(DATABASE), read_only=True)
    try:
        row = connection.execute(
            """
            SELECT
                COUNT(*) AS lodgements,
                ROUND(MEDIAN(weekly_rent), 2) AS median_weekly_rent
            FROM rental_bonds
            WHERE postcode = ?
              AND dwelling_type = ?
              AND bedrooms = ?
              AND rent_status = 'valid'
            """,
            [postcode, code, bedrooms],
        ).fetchone()
    finally:
        connection.close()

    lodgements, median = row
    if lodgements == 0:
        return {
            "postcode": postcode,
            "message": "No matching records with valid rents were found.",
        }

    return {
        "source": "NSW Fair Trading rental bond lodgements, 2025",
        "postcode": postcode,
        "dwelling_type": code,
        "bedrooms": bedrooms,
        "lodgements": int(lodgements),
        "median_weekly_rent_aud": float(median),
        "small_sample": lodgements < 10,
    }


def monthly_rent_trend(
        postcode: str,
        dwelling_type: str,
        bedrooms: int,
) -> dict:
    """Get monthly 2025 median weekly rents and lodgement counts for one postcode, type, and bedroom count."""
    postcode = str(postcode).strip()

    if not postcode.isdigit() or len(postcode) > 4:
        return {"error": "Enter a valid four-digit postcode."}
    postcode = postcode.zfill(4)

    code = dwelling_type.strip().upper()
    aliases = {
        "HOUSE": "H",
        "HOUSES": "H",
        "FLAT": "F",
        "UNIT": "F",
        "TERRACE": "T",
        "TOWNHOUSE": "T",
        "OTHER": "O",
    }
    code = aliases.get(code, code)

    if code not in {"F", "H", "T", "O"}:
        return {"error": "Choose F, H, T, or O for dwelling type."}
    if not isinstance(bedrooms, int) or not 0 <= bedrooms <= 20:
        return {"error": "Bedrooms must be a whole number from 0 to 20."}

    connection = duckdb.connect(str(DATABASE), read_only=True)
    try:
        rows = connection.execute(
            """
            SELECT
                strftime(lodgement_date, '%Y-%m') AS month,
                COUNT(*) AS lodgements,
                ROUND(MEDIAN(weekly_rent), 2) AS median_weekly_rent
            FROM rental_bonds
            WHERE postcode = ?
              AND dwelling_type = ?
              AND bedrooms = ?
              AND rent_status = 'valid'
              AND lodgement_date >= DATE '2025-01-01'
              AND lodgement_date < DATE '2026-01-01'
            GROUP BY month
            ORDER BY month
            """,
            [postcode, code, bedrooms],
        ).fetchall()
    finally:
        connection.close()

    if not rows:
        return {
            "postcode": postcode,
            "message": "No matching records with valid rents were found.",
            "months": [],
        }

    return {
        "source": "NSW Fair Trading rental bond lodgements, 2025",
        "postcode": postcode,
        "dwelling_type": code,
        "bedrooms": bedrooms,
        "months": [
            {
                "month": month,
                "lodgements": int(lodgements),
                "median_weekly_rent_aud": float(median),
                "small_sample": lodgements < 10,
            }
            for month, lodgements, median in rows
        ],
    }