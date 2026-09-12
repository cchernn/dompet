import gzip
import re

COPY_RE = re.compile(r'^COPY public\.("?[\w]+"?) \(([^)]*)\) FROM stdin;$')


def _unescape(value: str):
    if value == r"\N":
        return None
    return (
        value.replace("\\t", "\t")
        .replace("\\n", "\n")
        .replace("\\r", "\r")
        .replace("\\\\", "\\")
    )


def parse_dump(path: str) -> dict[str, list[dict]]:
    """Parse a plain-text pg_dump file's COPY blocks into {table_name: [row_dict, ...]}.

    Only handles the tab-delimited COPY ... FROM stdin; format pg_dump emits by
    default for plain SQL dumps; does not execute or validate any SQL.
    """
    tables = {}
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as f:
        lines = f.readlines()

    i = 0
    n = len(lines)
    while i < n:
        m = COPY_RE.match(lines[i].rstrip("\n"))
        if not m:
            i += 1
            continue
        table_name = m.group(1).strip('"')
        columns = [c.strip().strip('"') for c in m.group(2).split(",")]
        i += 1
        rows = []
        while i < n and lines[i].rstrip("\n") != r"\.":
            raw = lines[i].rstrip("\n")
            fields = raw.split("\t")
            rows.append({col: _unescape(val) for col, val in zip(columns, fields)})
            i += 1
        tables[table_name] = rows
        i += 1  # skip the closing \.
    return tables
