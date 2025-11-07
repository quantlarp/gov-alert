name: Uniswap Governance Alerts

on:
  # Runs every 5 minutes (minimum GitHub cron granularity)
  schedule:
    - cron: "*/5 * * * *"

  # Manual trigger from the Actions tab (used for testing)
  workflow_dispatch:
    inputs:
      force_latest:
        description: "Send alert for latest topic (test mode)"
        required: false
        default: "false"

permissions:
  contents: write   # needed so we can commit the updated state JSON

jobs:
  run-alert:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install requests

      - name: Run Uniswap governance alert script
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
          # This will be "true"/"false" when run manually, empty on cron runs
          FORCE_LATEST: ${{ github.event.inputs.force_latest }}
        run: python uniswap_gov_alert.py

      - name: Commit updated state (if changed)
        run: |
          if git status --porcelain | grep -q "uniswap_last_seen.json"; then
            git config --global user.email "github-actions@users.noreply.github.com"
            git config --global user.name "GitHub Actions"
            git add uniswap_last_seen.json
            git commit -m "Update last_seen for Uniswap governance" || echo "No changes to commit"
            git push
          else
            echo "No state changes to commit."
          fi
