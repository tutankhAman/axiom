import csv
import logging

logger = logging.getLogger(__name__)


class EPWReader:
    def __init__(self, epw_path: str):
        self.epw_path = epw_path
        self._temperatures = []
        self._load()

    def _load(self):
        try:
            with open(self.epw_path) as f:
                reader = csv.reader(f)
                in_data = False
                for row in reader:
                    if in_data:
                        # Index 6 is Dry Bulb Temperature in EPW data rows
                        self._temperatures.append(float(row[6]))
                    elif row and row[0].startswith("DATA PERIODS"):
                        in_data = True
        except Exception as e:
            logger.error(f"Failed to load EPW file {self.epw_path}: {e}")

    def get_forecast(self, current_hour: float, hours: int) -> list[float]:
        if not self._temperatures:
            return []

        # Round current hour to nearest int
        idx = int(round(current_hour))
        forecast = []
        for i in range(1, hours + 1):
            if idx + i < len(self._temperatures):
                forecast.append(self._temperatures[idx + i])
            else:
                forecast.append(self._temperatures[-1])  # Fallback
        return forecast
