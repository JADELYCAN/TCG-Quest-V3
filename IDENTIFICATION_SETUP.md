# TCG Quest V3 — Photo identification

This release adds a photo-based AI identification helper for Pokémon, One Piece, and sports cards. It retains the manual green/yellow centering controls and the educational grading assistant.

## Install
Replace `app.py` and `index.html` in the root of the GitHub repository, keeping the other files. Commit changes and wait for Render to deploy.

## Enable AI recognition
In Render: open the TCG-Quest-V3 web service > Environment > Add Environment Variable. Set **Key** to `OPENAI_API_KEY` and **Value** to your own OpenAI API key. Save and redeploy. Never paste the key into GitHub or into the browser page. OpenAI API billing is separate from a ChatGPT subscription; image calls may incur charges. Optionally set `OPENAI_VISION_MODEL` to an available image-capable model (default `gpt-4o-mini`).

## What it does
- Upload a front card photo in the scanner and click **Identify Front Photo**.
- The server sends a resized photo to the configured AI vision provider.
- It suggests card category, name, set, number, year and variant, leaving fields blank when uncertain.
- A button copies the proposed card identity into the collection form; the user must verify it.
- Does **not** independently verify a card against an authoritative catalog, guarantee correct variants, identify counterfeits, or establish PSA grades.
- Without an API key, the feature shows a clear disabled state rather than making up identification results.

## Privacy and safety
Photos are transmitted to the configured third-party vision API when the user clicks Identify. Photos are not stored by this new endpoint. The API key stays on the server. Uploaded photos are limited to 6 MB. Avoid uploading photos with private information.
