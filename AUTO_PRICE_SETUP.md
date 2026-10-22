# Automatic photo-to-price search — TCG Quest V3

Replace only the repository root `index.html` with this updated file. Leave `app.py` and other files unchanged if they are from the latest TCG Quest V3 Price Comparison package.

## What happens
Selecting or taking a front photo triggers `/api/identify` automatically, then fills the marketplace query with the suggested card name, number, set and variant. It immediately requests the eBay listing search (when configured) and creates PriceCharting/TCGplayer search links. No extra Analyze or Identify button is required. The identification result remains editable; retry identification is available.

## Requirements
- `OPENAI_API_KEY` configured in Render Environment and `/api/identify/status` reports available. API calls may incur charges.
- `EBAY_CLIENT_ID` and `EBAY_CLIENT_SECRET` plus eBay Browse API access for embedded eBay asking prices.
- PriceCharting and TCGplayer are search links until permitted pricing feeds are connected.

## Limitations
The AI can misidentify sets, variants or numbers; verify results. Active listing prices are not sold prices. If the AI is not configured, the user can still enter the card manually. Re-selecting a photo can cause another billable API request. No secret keys are placed in HTML.
