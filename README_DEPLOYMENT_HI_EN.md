# BATKAHI AI — Online Multi-user Deployment

This package adapts the existing Streamlit app for online hosting with one shared PostgreSQL database. SQLite remains available for local testing.

## Included
- One online web URL for the team.
- Shared PostgreSQL storage for news, RSS settings, channels and app settings.
- Existing Home, Categories, News Radar, filters and sorting retained.
- Initial release uses one shared admin login/password. Anyone with the password has the same access.

## Deploy on Render
1. Create a GitHub repository and upload `batkahi_ai.py`, `requirements.txt`, and `render.yaml`.
2. Push the repository to GitHub.
3. In Render, choose **New → Blueprint** and connect that repository.
4. Render reads `render.yaml` and provisions the web service and PostgreSQL database.
5. When prompted for `BATKAHI_ADMIN_USERNAME` and `BATKAHI_ADMIN_PASSWORD`, set a team Login ID and a long, unique password. Do not use `admin123`.
6. Deploy, open the web service URL, and sign in with that password.
7. In Settings, configure RSS feed URLs.

## Important
- The blueprint uses a paid web service and managed PostgreSQL plan. Check Render's current pricing before provisioning.
- All users of this deployment share the same database. Do not create separate app deployments if everyone needs the same workspace.
- This cloud release uses one shared Login ID and Password for the whole team. Anyone with both credentials has the same access; there are no individual accounts or roles. Add individual accounts, roles and audit logs before inviting a large team.
- RSS feeds are fetched when a logged-in user clicks **Refresh News**; there is no background scheduler yet.
- Categorization is currently keyword-based, not semantic AI classification.
- Back up the PostgreSQL database regularly.

## Run locally
```bash
pip install -r requirements.txt
# Windows PowerShell:
$env:BATKAHI_ADMIN_PASSWORD="Choose-A-Long-Unique-Password"
streamlit run batkahi_ai.py
```
Without `DATABASE_URL`, local SQLite is used at `data/batkahi_ai.db`. With `DATABASE_URL`, PostgreSQL is used.

## Environment variables
- `DATABASE_URL`: PostgreSQL connection string; leave unset for local SQLite.
- `BATKAHI_ADMIN_USERNAME`: initial shared Login ID on a fresh database (default `admin`).\n- `BATKAHI_ADMIN_PASSWORD`: initial shared password on a fresh database.
- `BATKAHI_DB_PATH`: optional SQLite file path.
