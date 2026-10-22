# TCG Quest V3 — Collection Value & Profit Chart

Replace only the repository-root `index.html` with this file. Keep your existing `app.py` and other files.

## Behavior
- Green line: sum of current estimated card values.
- Purple line: current estimated values minus values entered when each card was added (NOT minus purchase price).
- Use Update value on any saved card to record new current value without changing its initial baseline.
- Stores up to 730 daily history entries in this browser using localStorage. Multiple changes on one day replace that day's snapshot.
- Historical data cannot be reconstructed from past dates; existing collections start with a snapshot at installation.
- New cards start with zero gain; adding/removing cards changes portfolio totals.
- This is not automatic marketplace pricing, account sync, or investment-grade return calculation.
- Export CSV includes initial and current values but not chart history.
