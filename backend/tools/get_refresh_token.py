"""
One-time script to get a Gmail OAuth refresh token.

Run this ONCE on your local machine (not on Render):
    cd backend
    python tools/get_refresh_token.py

It will open a browser window, ask you to log in to Google,
then print your refresh token. Copy it to Render's environment variables.

Prerequisites:
    pip install google-auth-oauthlib

You need credentials.json downloaded from Google Cloud Console.
See the setup instructions in the project README.
"""
import json
import os
import sys

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("ERROR: google-auth-oauthlib not installed.")
    print("Run:  pip install google-auth-oauthlib")
    sys.exit(1)

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# Look for credentials.json in the same folder as this script,
# or in the backend/ root.
SEARCH_PATHS = [
    os.path.join(os.path.dirname(__file__), "credentials.json"),
    os.path.join(os.path.dirname(__file__), "..", "credentials.json"),
]

creds_path = next((p for p in SEARCH_PATHS if os.path.exists(p)), None)

if not creds_path:
    print("\nERROR: credentials.json not found.")
    print("Download it from Google Cloud Console:")
    print("  1. Go to console.cloud.google.com")
    print("  2. APIs & Services → Credentials")
    print("  3. Click your OAuth 2.0 Client ID → Download JSON")
    print("  4. Save it as  backend/tools/credentials.json")
    sys.exit(1)

print(f"\nUsing credentials from: {creds_path}")
print("A browser window will open. Log in with amols.emailid@gmail.com\n")

flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
creds = flow.run_local_server(port=0)

print("\n" + "=" * 60)
print("SUCCESS! Copy these values into Render's Environment variables:")
print("=" * 60)
print(f"\nGMAIL_CLIENT_ID     = {creds.client_id}")
print(f"GMAIL_CLIENT_SECRET = {creds.client_secret}")
print(f"GMAIL_REFRESH_TOKEN = {creds.refresh_token}")
print(f"GMAIL_USER          = amols.emailid@gmail.com")
print("\n" + "=" * 60)

# Also save to a local .env snippet for convenience
snippet_path = os.path.join(os.path.dirname(__file__), "gmail_env_vars.txt")
with open(snippet_path, "w") as f:
    f.write(f"GMAIL_CLIENT_ID={creds.client_id}\n")
    f.write(f"GMAIL_CLIENT_SECRET={creds.client_secret}\n")
    f.write(f"GMAIL_REFRESH_TOKEN={creds.refresh_token}\n")
    f.write(f"GMAIL_USER=amols.emailid@gmail.com\n")
print(f"Also saved to: {snippet_path}")
