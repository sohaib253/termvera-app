import logging
import sys


def setup_logging(environment: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    fmt = (
        "%(asctime)s level=%(levelname)s logger=%(name)s "
        "request_id=%(request_id)s message=%(message)s"
    )
    handler.setFormatter(_RequestIdFormatter(fmt))

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO if environment == "production" else logging.DEBUG)

    # Never let a third-party library log full request/response bodies at INFO.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


class _RequestIdFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return super().format(record)
