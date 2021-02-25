from datetime import datetime


def from_iso8601(startdate_iso: str):
    return datetime.strptime(startdate_iso, "%Y-%m-%dT%H:%M:%S.%f%z")
