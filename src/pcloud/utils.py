import datetime
import logging
import sys

log = logging.getLogger("pcloud")
log.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stderr)
handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
log.addHandler(handler)

# Helpers
def to_api_datetime(dt):
    """Converter to a datetime structure the pCloud API understands

    See https://docs.pcloud.com/structures/datetime.html
    """
    if isinstance(dt, datetime.datetime):
        return dt.isoformat()
    return dt