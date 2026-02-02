name: Pickleball Data Sync

on:
  schedule:
    - cron: '0 */6 * * *' # Runs every 6 hours
  workflow_dispatch: # Allows you to run it manually button click

jobs:
  sync-data:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run Extraction Script
        env:
          FIREBASE_SERVICE_ACCOUNT_KEY: ${{ secrets.FIREBASE_SERVICE_ACCOUNT_KEY }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          DRIVE_FOLDER_ID: ${{ secrets.DRIVE_FOLDER_ID }}
        run: python main.py
