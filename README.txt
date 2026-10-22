TCG QUEST V3 — AI CARTOON COLLECTOR UPGRADE

FILES TO REPLACE IN THE ROOT OF YOUR GITHUB REPOSITORY:
- index.html
- app.py

NEW FILE TO ADD:
- avatar_api.py

KEEP THESE IMAGE FILES IN YOUR REPOSITORY:
- reference-banner.png, reference-logo.png, nav-1.png ... nav-9.png,
  action-1.png ... action-4.png, feature-1.png ... feature-4.png.
(The ZIP includes copies if any are missing.)

RENDER SETUP:
1. In Render, open your TCG Quest web service > Environment.
2. Add OPENAI_API_KEY with your own OpenAI API key (do not put the key in GitHub or HTML).
3. Optional: OPENAI_IMAGE_MODEL=gpt-image-1.5. Your API account needs access to this model and billing.
4. Redeploy. Existing start command: gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
   Image generation may take longer than 120 seconds; if requests time out,
   raise the timeout to 240 seconds or move generation to a background job.
5. On your website: My Collector Identity > upload selfie > choose hat/clothes > Generate.

PRIVACY AND LIMITATIONS:
- The uploaded selfie is sent to the image-generation API on Generate.
- Generated banner and preferences are saved to browser localStorage only; no accounts or cloud sync.
- Image editing is probabilistic; the new cartoon likeness may require retrying.
- To preserve other artwork, only the central masked character region is composited onto the original banner.
- Float + Glow applies subtle motion/glow to the banner. Independent character animation would require
  layered character artwork and more advanced segmentation/animation.
- AI requests incur charges. Add rate limits, login, quotas and moderation before opening to the public.
- Existing collection data keys and scanner routes are not intentionally changed.
