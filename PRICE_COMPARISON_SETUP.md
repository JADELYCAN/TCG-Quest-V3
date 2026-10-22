# TCG Quest V3 — Three-source price comparison

## Installation
Replace **index.html** in the repository root with the included file. The existing app.py from the Rewards update already includes the eBay `/api/market/search` endpoint; no backend changes are required for this update. Keep your other files.

## Features
- Price comparison search under Marketplace.
- Clicking a source opens its marketplace search.
- With eBay production credentials and Browse API access, displays the lowest returned active eBay asking price and can link to that listing.
- After AI card identification, **Compare prices for this card** fills the card name, set, number and variant.
- PriceCharting and TCGplayer are links only, not embedded prices, until authorized pricing API access is obtained.

## Accuracy
An eBay listing may not match the exact variant, condition, grade or edition. A lowest asking price is not a verified market value. Do not present it as a sold price.
