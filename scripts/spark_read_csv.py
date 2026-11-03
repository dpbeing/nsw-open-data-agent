from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql.types import DateType, StringType, StructField, StructType


PROJECT_ROOT = Path(__file__).resolve().parents[1]
csv_path = PROJECT_ROOT / "data" / "interim" / "rental_bonds_2025.csv"

schema = StructType(
    [
        StructField("lodgement_date", DateType(), True),
        StructField("postcode", StringType(), True),
        StructField("dwelling_type_raw", StringType(), True),
        StructField("bedrooms_raw", StringType(), True),
        StructField("weekly_rent_raw", StringType(), True),
    ]
)

spark = (
    SparkSession.builder
    .appName("rental-bond-data")
    .master("local[2]")
    .config("spark.sql.shuffle.partitions", "2")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("ERROR")

try:
    lodgements = (
        spark.read
        .option("header", "true")
        .option("dateFormat", "yyyy-MM-dd")
        .schema(schema)
        .csv(str(csv_path))
    )

    lodgements.printSchema()
    print("Rows:", lodgements.count())
    lodgements.show(5, truncate=False)
finally:
    spark.stop()