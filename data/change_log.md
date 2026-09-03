# Change log

Source: `data/messy_sample.csv`
Output: `data/cleaned_sample.csv`

- Rows in: **14**
- Rows out: **9**

## What changed

- Blank rows removed: **2**
- Duplicate people merged (matched on email, case-insensitive): **3**
- Names trimmed and cased consistently: **4**
- Dates converted to ISO (YYYY-MM-DD): **10**
- Amounts split into a number and a currency code: **10**
- Country names standardised: **4**
- Phone numbers stripped to digits and a country prefix: **12**

## Left alone on purpose

- `Signup Date` values I could not read without guessing:
  - line 14: 'Q2 2024'
- `Amount` values I could not read without guessing:
  - line 14: 'approx 800'
  - line 15: 'TBC'

These are flagged rather than invented. Ambiguous input is a question for the client, not something to silently fill in.
