# Automation demo — scrape, clean, alert

A small, working example of the three things I do most: pull data off a website,
turn a messy export into something usable, and wire it into a workflow that runs
on a schedule without anyone watching it.

Everything here runs. The numbers below are from an actual run, not a mock-up.

---

## 1. Scraper — `scrape_books.py`

Walks a paginated catalogue and writes a typed CSV.

```bash
python scrape_books.py --pages 5 --out data/books_scraped.csv
```

Real output from the run committed here:

```
100 rows -> data/books_scraped.csv
  priced rows: 100  avg GBP 34.56
```

| title | price_gbp | rating | in_stock | source_page |
|---|---|---|---|---|
| A Light in the Attic | 51.77 | 3 | True | 1 |
| Tipping the Velvet | 53.74 | 1 | True | 1 |
| Soumission | 50.10 | 1 | True | 1 |

What is worth noticing in the code rather than the output:

- **Retries with backoff** on transient network errors, so one blip does not kill a run.
- **`parse_price` returns `None` instead of guessing** if the price format changes.
- **A polite delay and a real User-Agent.** It identifies itself.
- Target is `books.toscrape.com`, a sandbox published specifically for scraping practice,
  so this demo has no terms-of-service or rate-limit argument to have. Client work gets
  the same structure pointed at a source we have agreed is fair game.

## 2. Cleaner — `clean_data.py`

Takes a deliberately awful export and produces a clean file **plus a written record of
every change**.

```bash
python clean_data.py --in data/messy_sample.csv --out data/cleaned_sample.csv
```

Real output:

```
14 rows in -> 9 rows out
  Blank rows removed: 2
  Duplicate people merged (matched on email, case-insensitive): 3
  Names trimmed and cased consistently: 4
  Dates converted to ISO (YYYY-MM-DD): 10
  Amounts split into a number and a currency code: 10
  Country names standardised: 4
  Phone numbers stripped to digits and a country prefix: 12
```

Before:

```
 John  Smith ,JOHN.SMITH@example.com,12/03/2024,"£1,299.00",UK,+44 20 7946 0958
JOHN SMITH,john.smith@example.com,12/03/2024,"£1,299.00",U.K.,+44 20 7946 0958
Amara  Okafor,AMARA.OKAFOR@EXAMPLE.COM,14 March 2024,"€ 2.100,00",Germany,+49 30 901820
```

After:

```
John Smith,john.smith@example.com,2024-03-12,1299.00,GBP,United Kingdom,+442079460958
Amara Okafor,amara.okafor@example.com,2024-03-14,2100.00,EUR,Germany,+4930901820
```

Five currency formats parse correctly, including the European convention where
`€ 2.100,00` means two thousand one hundred, not two point one. `Tom O'Brien` survives
title-casing with the apostrophe intact.

**The part I actually care about** is the end of `data/change_log.md`:

```
## Left alone on purpose

- `Signup Date` values I could not read without guessing:
  - line 14: 'Q2 2024'
- `Amount` values I could not read without guessing:
  - line 14: 'approx 800'
  - line 15: 'TBC'

These are flagged rather than invented. Ambiguous input is a question for the
client, not something to silently fill in.
```

A cleaner that quietly turns `TBC` into `0` is worse than useless, because you cannot
tell afterwards which numbers were real. Anything genuinely ambiguous gets flagged and
asked about.

## 3. Workflow — `workflows/daily-price-watch.n8n.json`

An importable n8n workflow: schedule → fetch → extract → clean → threshold check → alert.

Import it with **Workflows → Import from file**. It runs end to end with no credentials;
the final node is a placeholder where Slack or email plugs in.

Same defensive habits as the scraper:

- The HTTP node retries 3 times with a 2-second gap.
- The Code node **throws if it extracts zero rows**, so a site change surfaces as a loud
  failure instead of a silently empty digest.
- Unparseable prices are kept with `parsed_ok: false` rather than dropped.

---

## Running it yourself

```bash
pip install requests beautifulsoup4
python scrape_books.py --pages 5
python clean_data.py
```

Python 3.12. No API keys, no accounts, no paid services.

## Honest notes

- `data/messy_sample.csv` is synthetic. It is built to contain the specific problems real
  exports contain — duplicates, four date formats, five currency conventions, blank rows,
  three spellings of the same country — but no real person's data appears in this repo.
- The scrape target is a practice site on purpose. Client work targets whatever source we
  have agreed is appropriate.
- Every output is checked before it goes anywhere. Every number in this README came from
  running the code, not from describing it.

## Who made this

Umar M. — Computer Engineering diploma, Singapore Polytechnic.
I build automations and clean up data: n8n and Make workflows, web scraping, messy
spreadsheets, and Python scripts for the tasks you redo every week.
