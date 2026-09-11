# Backend Agent Guidance

## Access And Organization Contract

The backend owns authentication and authorization decisions. On login, look up the user by unique username, validate the password, confirm `active` status, then return the user's organization, profile, and allowed entry point.

Expected profiles:

- `platform_admin`: can manage organizations, organization users, and purchased tiers.
- `organization_admin`: can manage members only within their own organization, constrained by that organization's assigned member limit.
- `member`: can access the normal application interface.

Organization, user status, profile, tier, and member-limit checks must be enforced in backend services and tables. Frontend routing should consume these backend decisions rather than duplicate them.

Keep the detailed implementation design in `docs/access-routing-design.md` until database models and API contracts are finalized.
