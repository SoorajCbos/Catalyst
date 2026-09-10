# Central All User App

Based on login username and organization associated with it, gives access to the user of that organization.

---


## Design of App 
backend/
|
|-app/
|   |-api/
|   |   |-v1/
|   |   |   |-routes/
|   |   |   |   |-agents.py
|   |   |   |   |-health.py
|   |   |-api.py
|   |-agents
|   |-tools
|   |-core
|   |-models
|   |-services
|   |-tables
|   |-main.py
|-tests/
|-docs/
|-AGENTS.md
|-README.md
|-requirements.txt

frontend/
|-app/
|   |-layout.tsx
|   |-page.tsx
|   |-globals.css
|-public/
|-AGENTS.md
|-CLAUDE.md
|-README.md
|-next.config.ts

## Access Design

The first frontend screen is a login page where the user enters a unique username and password. The username is not required to be an email address.

After login, the backend must look up the user table by username, validate the password, confirm the user is active, and load the user's organization, profile, and organization tier/member limits.

There are three entry points after authentication:

- Platform admin: route to the platform administration interface for adding organizations, adding users to organizations, and assigning the purchased organization tier.
- Organization admin: route to the organization administration interface for adding members only to their own organization, limited by the member count assigned to that organization.
- Member: route to the normal application interface. This interface will be designed later.

The backend is the source of truth for organization membership, active status, profile, tier, and member limit checks. The frontend should route based on the authenticated response from the backend, not on local assumptions.

See `backend/docs/access-routing-design.md` for the current concise design contract.