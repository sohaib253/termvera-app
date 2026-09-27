import logging
import sys
from logging.handlers import RotatingFileHandler


def setup_logging(environment: str, log_file: str | None = None) -> None:
    # The desktop app has no console (sys.stdout is None), so it logs to a
    # rotating file in its data folder instead.
    handler: logging.Handler
    if log_file:
        handler = RotatingFileHandler(log_file, maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    else:
        handler = logging.StreamHandler(sys.stdout)
    fmt = (
        "%(asctime)s level=%(levelname)s logger=%(name)s "
        "request_id=%(request_id)s message=%(message)s"
    )
    handler.setFormatter(_RequestIdFormatter(fmt))

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO if environment in ("production", "desktop") else logging.DEBUG)

    # Never let a third-party library log full request/response bodies at INFO.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


class _RequestIdFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return super().format(record)
