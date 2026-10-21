# TCG Quest scanner detection fix

Updated `app.py` to recognize rounded-corner trading cards against light backgrounds using foreground segmentation and rotated rectangles, falling back to the existing four-point edge detector. This addresses the previous 'Could not automatically find four card corners' error.

## Deploy
Your Render service has Root Directory `tcg_quest_v2`. On GitHub, open `tcg_quest_v2/app.py`, click Edit, and replace its contents with this package's `tcg_quest_v2/app.py`. Commit changes; Render will redeploy. Do not upload the ZIP itself to GitHub.

## Limits
Detected outer corners are estimates, and the printed-frame measurements remain heuristic. Confirm the overlay matches the true border. No validated PSA grade is generated.
