"""Strict parsing of CSV boolean flags."""

def parse_csv_bool(value, *, field="flag"):
    """Accept common textual boolean literals; reject ambiguous clinical flags."""
    if isinstance(value, bool):
        return value
    if value is None or str(value).strip() == "":
        return False
    token = str(value).strip().lower()
    if token in {"1", "true", "t", "yes", "y"}:
        return True
    if token in {"0", "false", "f", "no", "n"}:
        return False
    raise ValueError(f"Invalid {field}: {value!r}. Use true/false, yes/no, or 1/0.")
