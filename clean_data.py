"""
Turn a messy client export into a clean file, and write down every change made.

The change log is the point. Anyone can hand back a tidier spreadsheet; the
useful part is being able to say exactly which rows were merged, which values
were reformatted, and which ones I refused to guess at.

Usage:
    python clean_data.py --in data/messy_sample.csv --out data/cleaned_sample.csv
"""

import argparse
import csv
import io
import re
from collections import Counter, defaultdict
from datetime import datetime

# Date formats seen in the wild, tried in order. Day-first before month-first,
# because this sample is UK/EU heavy; a real job pins this down with the client
# rather than guessing.
DATE_FORMATS = [
    "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y",
    "%d %B %Y", "%d %b %Y", "%b %d %Y", "%B %d %Y",
]

CURRENCY_SYMBOLS = {"£": "GBP", "$": "USD", "€": "EUR", "¥": "CNY", "₹": "INR"}

COUNTRY_CANON = {
    "uk": "United Kingdom", "u.k.": "United Kingdom", "united kingdom": "United Kingdom",
    "gb": "United Kingdom",
    "usa": "United States", "us": "United States", "u.s.": "United States",
    "united states": "United States",
    "de": "Germany", "germany": "Germany",
    "china": "China", "cn": "China",
    "india": "India", "in": "India",
}


def squash(text):
    """Collapse runs of whitespace and trim. Nothing clever, just consistent."""
    return re.sub(r"\s+", " ", (text or "")).strip()


def title_name(text):
    """Title-case a name without destroying surnames like O'Brien."""
    cleaned = squash(text)
    if not cleaned:
        return ""
    parts = []
    for word in cleaned.split(" "):
        if "'" in word:
            head, _, tail = word.partition("'")
            parts.append(head.capitalize() + "'" + tail.capitalize())
        else:
            parts.append(word.capitalize())
    return " ".join(parts)


def parse_date(text):
    """Return (iso_date, matched_format), or (None, None) if nothing fits."""
    cleaned = squash(text)
    if not cleaned:
        return None, None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date().isoformat(), fmt
        except ValueError:
            continue
    return None, None


def parse_amount(text):
    """
    Split a display amount into (currency_code, float).

    European format (dot thousands, comma decimals) is detected by the comma
    sitting closer to the end than the dot, which is the only reliable tell
    without knowing the locale up front.
    """
    cleaned = squash(text)
    if not cleaned:
        return None, None
    currency = None
    for symbol, code in CURRENCY_SYMBOLS.items():
        if symbol in cleaned:
            currency = code
            cleaned = cleaned.replace(symbol, "")
            break
    cleaned = squash(cleaned)
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")   # 2.100,00 -> European
        else:
            cleaned = cleaned.replace(",", "")                      # 1,299.00 -> Anglo
    else:
        cleaned = cleaned.replace(",", "")
    try:
        return currency, round(float(cleaned), 2)
    except ValueError:
        return currency, None


def normalise_phone(text):
    """Keep digits and a leading +, drop the decorative punctuation."""
    cleaned = squash(text)
    if not cleaned:
        return ""
    plus = cleaned.startswith("+")
    digits = re.sub(r"\D", "", cleaned)
    return ("+" if plus else "") + digits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", default="data/messy_sample.csv")
    ap.add_argument("--out", dest="dst", default="data/cleaned_sample.csv")
    ap.add_argument("--log", dest="log", default="data/change_log.md")
    args = ap.parse_args()

    with io.open(args.src, encoding="utf-8", newline="") as fh:
        raw_rows = list(csv.DictReader(fh))

    stats = Counter()
    unparsed = defaultdict(list)
    by_email = {}
    order = []

    for line_no, row in enumerate(raw_rows, start=2):
        values = {k: (v or "") for k, v in row.items()}
        if not any(squash(v) for v in values.values()):
            stats["blank_rows_dropped"] += 1
            continue

        email = squash(values.get("Email", "")).lower()

        name = title_name(values.get("Customer Name", ""))
        if name != squash(values.get("Customer Name", "")):
            stats["names_reformatted"] += 1

        iso_date, fmt = parse_date(values.get("Signup Date", ""))
        if iso_date is None:
            unparsed["Signup Date"].append(
                "line {}: {!r}".format(line_no, values.get("Signup Date", "")))
        elif fmt != "%Y-%m-%d":
            stats["dates_reformatted"] += 1

        currency, amount = parse_amount(values.get("Amount", ""))
        if amount is None:
            unparsed["Amount"].append(
                "line {}: {!r}".format(line_no, values.get("Amount", "")))
        else:
            stats["amounts_parsed"] += 1

        raw_country = squash(values.get("Country", ""))
        country = COUNTRY_CANON.get(raw_country.lower(), raw_country)
        if country != raw_country:
            stats["countries_normalised"] += 1

        phone = normalise_phone(values.get("Phone", ""))
        if phone != squash(values.get("Phone", "")):
            stats["phones_normalised"] += 1

        record = {
            "customer_name": name,
            "email": email,
            "signup_date": iso_date or "",
            "amount": "" if amount is None else "{:.2f}".format(amount),
            "currency": currency or "",
            "country": country,
            "phone": phone,
        }

        if email and email in by_email:
            stats["duplicate_rows_merged"] += 1
            existing = by_email[email]
            # Keep the more complete version of each field rather than blindly
            # taking whichever row happened to come first.
            for key, value in record.items():
                if not existing.get(key) and value:
                    existing[key] = value
            continue

        if email:
            by_email[email] = record
        order.append(record)

    fields = ["customer_name", "email", "signup_date", "amount", "currency", "country", "phone"]
    with io.open(args.dst, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(order)

    labels = [
        ("blank_rows_dropped", "Blank rows removed"),
        ("duplicate_rows_merged", "Duplicate people merged (matched on email, case-insensitive)"),
        ("names_reformatted", "Names trimmed and cased consistently"),
        ("dates_reformatted", "Dates converted to ISO (YYYY-MM-DD)"),
        ("amounts_parsed", "Amounts split into a number and a currency code"),
        ("countries_normalised", "Country names standardised"),
        ("phones_normalised", "Phone numbers stripped to digits and a country prefix"),
    ]

    lines = [
        "# Change log",
        "",
        "Source: `{}`".format(args.src),
        "Output: `{}`".format(args.dst),
        "",
        "- Rows in: **{}**".format(len(raw_rows)),
        "- Rows out: **{}**".format(len(order)),
        "",
        "## What changed",
        "",
    ]
    for key, label in labels:
        lines.append("- {}: **{}**".format(label, stats.get(key, 0)))

    lines += ["", "## Left alone on purpose", ""]
    if unparsed:
        for column, examples in unparsed.items():
            lines.append("- `{}` values I could not read without guessing:".format(column))
            for example in examples:
                lines.append("  - {}".format(example))
        lines.append("")
        lines.append("These are flagged rather than invented. Ambiguous input is a question "
                     "for the client, not something to silently fill in.")
    else:
        lines.append("Nothing. Every value parsed cleanly.")
    lines.append("")

    with io.open(args.log, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    print("{} rows in -> {} rows out".format(len(raw_rows), len(order)))
    for key, label in labels:
        if stats.get(key):
            print("  {}: {}".format(label, stats[key]))
    print("change log -> {}".format(args.log))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
