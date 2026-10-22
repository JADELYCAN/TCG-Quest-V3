# TCG Quest V3 — Marketplace Upgrade

## Included
- eBay Browse API active-listing search for Pokémon, One Piece and sports cards
- Category and condition filters, sorting by asking price
- USD listing-count, median and price range (active listing asking prices only)
- Shipping information where returned
- External search links for eBay, TCGplayer and PriceCharting without credentials
- Preserves scanner, manual line adjustment, grading assistant, and AI photo identification

## Render configuration
1. In Render, open TCG-Quest-V3 > Environment.
2. Set `EBAY_CLIENT_ID` and `EBAY_CLIENT_SECRET` to valid eBay production application credentials.
3. Ensure your eBay application has access to the Browse API.
4. Redeploy and test a search. Never place credentials in GitHub.

## Limitations
The price statistics are calculated from the returned active listings, not completed sales or a verified market price. Different card variants, conditions, and grades may be mixed. TCGplayer and PriceCharting links open external sites; they are not API integrations. Live eBay search requires API access. This update does not alter local collection estimated values automatically.

## Installation
Replace root `app.py` and `index.html` in GitHub with these files. Add this README optionally. Keep the remaining files as-is. Do not upload a ZIP directly.
