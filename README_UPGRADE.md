# TCG Quest v2 — Flashy site + measurement scanner + market search

## Included
- Responsive neon landing page and animated card hero.
- OpenCV automatic perspective correction and experimental border measurements for front/back images.
- Local-browser collection vault and CSV export.
- New live eBay Browse API **active listings** search, enabled only after providing approved eBay production API credentials.
- Explicit TCGplayer integration placeholder. Approved TCGplayer API access is required; an API token alone does not activate an adapter.

## Not included / limitations
- Not a validated PSA grade predictor: no verified corner, edge, surface, or print-defect model.
- eBay asking prices are not sold/comps data and should not be labeled market value.
- TCGplayer pricing and catalog are not live until approved access and adapter are built.
- Collection vault is browser-local, not a server-backed account.

## Render deployment
Upload all project files to your GitHub repository root. Render settings: Python, build command `pip install -r requirements.txt`, start command `gunicorn app:app --bind 0.0.0.0:$PORT`. Set EBAY_CLIENT_ID and EBAY_CLIENT_SECRET under Render > Environment if you have eBay Developer production API access, then redeploy. Never expose secrets in HTML or commit them to GitHub.

## Local run
`pip install -r requirements.txt && python app.py`

## Roadmap
1. Add consent-based image uploads, photo-quality gating, measurable confidence and datasets of known graded cards.
2. Train/evaluate defect detectors for corners, edges and surfaces; display uncertain estimates only after validation.
3. Integrate approved TCGplayer data and compliant eBay sold-data provider where permitted.
4. Add persistent accounts, inventory database, price history and alerts.
