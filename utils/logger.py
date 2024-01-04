import pytz
from datetime import datetime
from typing import Optional


class TimeZoneLogger:
    INFO_COLOR = "\033[94m"  # Blue
    ERROR_COLOR = "\033[91m"  # Red
    SUCCESS_COLOR = "\033[92m"  # Green
    RESET_COLOR = "\033[0m"  # Reset color to default

    def __init__(self, zone: str, filename: Optional[str] = None):
        self.timezone = pytz.timezone(zone)
        self.filename = filename

    def _get_current_dt(self):
        return datetime.now(self.timezone)

    def _log(self, message: str):
        if self.filename:
            with open(self.filename, "a") as fd:
                fd.write(message + "\n")
        print(message)

    def info(self, message: str):
        self._log(
            f"[{self.INFO_COLOR}*{self.RESET_COLOR}] ({self._get_current_dt()}) - {message}"
        )

    def error(self, message: str):
        self._log(
            f"[{self.ERROR_COLOR}!{self.RESET_COLOR}] ({self._get_current_dt()}) - {message}"
        )

    def success(self, message: str):
        self._log(
            f"[{self.SUCCESS_COLOR}+{self.RESET_COLOR}] ({self._get_current_dt()}) - {message}"
        )


log = TimeZoneLogger(zone="Asia/Jakarta", filename="logs/run.log")
