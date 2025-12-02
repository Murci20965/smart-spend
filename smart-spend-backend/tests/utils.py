def csv_bytes_from_rows(rows: list[dict]) -> bytes:
    """Create CSV bytes from a sequence of row dicts.

    Each row should be a mapping with the same keys. The function writes a
    header derived from the first row and returns UTF-8 encoded bytes.
    """
    import csv
    import io

    buf = io.StringIO()
    writer = csv.writer(buf)
    # write header using keys from first row
    header = list(rows[0].keys())
    writer.writerow(header)
    for r in rows:
        writer.writerow([r.get(k, "") for k in header])
    return buf.getvalue().encode("utf-8")
