# TCG Quest — deployable website

This is a working Flask website with a flashy mobile-responsive frontend, experimental OpenCV card centering measurement, and a local-browser collection tracker. **It is not an official PSA grader and does not reliably predict a PSA grade.** It is not yet a live hosted website.

## Run locally

1. Install Python 3.10+
2. Run `pip install -r requirements.txt`
3. Run `python app.py`
4. Visit `http://localhost:5050`

## Publish on Render

1. Put the files in this folder in a GitHub repository.
2. On Render.com create a **Blueprint** service from that repository (the included `render.yaml` sets up a Python web service).
3. Once deployed, Render will provide a public HTTPS URL. You may connect a custom domain through the hosting dashboard.

## Important limitations

- Scanner: computer vision measures possible border ratios; check the drawn lines. Results may be wrong for borderless cards, foil glare, perspective or busy artwork. No reliable PSA grade is generated.
- Portfolio: saved only in this browser's localStorage. Export a CSV to back it up. No accounts, syncing, or live market data.
- Public production launch needs rate limiting, file validation/security hardening, privacy policy, user accounts, scalable storage, testing, and legal review for prizes.
- No affiliation with PSA, Pokémon, One Piece, or card manufacturers.
