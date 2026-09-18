# Access Routing Design

## Purpose

The application starts with a login page. A user enters a unique username and password. The username does not need to be an email address.

## Backend Responsibility

On login, the backend checks the user table for the submitted username, validates the password, confirms the user is active, and loads the assigned organization, profile, tier, and member limits.

The backend is the source of truth for:

- User active status
- User profile
- Organization assignment
- Organization tier
- Organization member limit

## Frontend Routing

After authentication, the frontend routes according to the backend response:

- Platform admin: page for adding organizations, adding users to organizations, and assigning purchased tiers.
- Organization admin: page for adding members to the admin's own organization, up to the assigned member limit.
- Member: normal app interface, to be provided later.

## Current Rule

Frontend pages should display the correct entry point, but backend services must enforce all organization and permission checks.