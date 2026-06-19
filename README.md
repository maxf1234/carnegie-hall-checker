# Carnegie Hall Event Monitor

Watches the Jacob Collier event page (Sept 30, 2026) for any change and sends an email alert.

## Setup

1. Add three repository secrets under Settings → Secrets and variables → Actions:
   - `EMAIL_SENDER` — your Gmail address
   - `EMAIL_PASSWORD` — your Gmail App Password
   - `EMAIL_RECIPIENT` — recipient(s), comma-separated for multiple

2. Trigger via the Actions tab (Run workflow) or set up cron-job.org to POST to:
   `https://api.github.com/repos/USERNAME/REPO/dispatches`
   with body `{"event_type": "run-monitor"}` and a GitHub token in the Authorization header.

## How it works

Fetches the page, strips out volatile content (tokens, timestamps), hashes the rest,
and alerts when the hash changes. State is stored in `state.json`, committed back to the repo.
