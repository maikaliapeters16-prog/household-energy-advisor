"""Settings: file locations, banner text and the month length. Change them here, nowhere else."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

TARIFF_PATH = BASE_DIR / "data" / "tariff.json"
APPLIANCES_PATH = BASE_DIR / "data" / "demo" / "appliances.csv"
TEST_HOUSEHOLDS_PATH = BASE_DIR / "data" / "demo" / "test_households.json"
SAMPLE_BILLS_DIR = BASE_DIR / "data" / "demo" / "sample_bills"

BANNER_TEXT = "Research Prototype: Simulated Utility Data"
DAYS_PER_MONTH = 30
