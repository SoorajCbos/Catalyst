"use client";

import { FormEvent, useEffect, useState } from "react";

type Organization = {
  recordId: string;
  name: string;
  tier: string;
  memberLimit: number;
};

type User = {
  recordId: string;
  username: string;
  email: string;
  organizationId: string;
  active: boolean;
  profile: string;
};

type CreatedUser = User & {
  // The backend returns this only once, immediately after creation.
  defaultPassword: string;
};

export default function UserManagementPage() {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [selectedOrganizationId, setSelectedOrganizationId] = useState("");

  const [users, setUsers] = useState<User[]>([]);
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [profile, setProfile] = useState("member");

  const [defaultPassword, setDefaultPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function loadOrganizations() {
    const response = await fetch("/api/v1/organizations");

    if (!response.ok) {
      throw new Error("Could not load organizations.");
    }

    const data = (await response.json()) as Organization[];

    setOrganizations(data);

    // Select the first organization automatically when one exists.
    if (data.length > 0) {
      setSelectedOrganizationId((current) => current || data[0].recordId);
    }
  }

  async function loadUsers(organizationId: string) {
    if (!organizationId) {
      setUsers([]);
      return;
    }

    const response = await fetch(
      `/api/v1/users?organizationId=${encodeURIComponent(organizationId)}`
    );

    if (!response.ok) {
      throw new Error("Could not load users.");
    }

    setUsers((await response.json()) as User[]);
  }

  // Load the organization list when the page first opens.
  useEffect(() => {
    async function loadPage() {
      try {
        await loadOrganizations();
      } catch (loadError) {
        setError(
          loadError instanceof Error
            ? loadError.message
            : "Could not load the page."
        );
      } finally {
        setIsLoading(false);
      }
    }

    void loadPage();
  }, []);

  // Reload the user list whenever another organization is selected.
  useEffect(() => {
    if (!selectedOrganizationId) {
      return;
    }

    async function refreshUsers() {
      try {
        setError("");
        await loadUsers(selectedOrganizationId);
      } catch (loadError) {
        setError(
          loadError instanceof Error
            ? loadError.message
            : "Could not load users."
        );
      }
    }

    void refreshUsers();
  }, [selectedOrganizationId]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setError("");
    setDefaultPassword("");
    setIsSubmitting(true);

    try {
      const response = await fetch("/api/v1/users", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: username.trim(),
          email: email.trim(),
          organizationId: selectedOrganizationId,
          profile,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail ?? "Could not create the user.");
      }

      const createdUser = data as CreatedUser;

      // Show the generated password once so the administrator can copy it.
      setDefaultPassword(createdUser.defaultPassword);

      setUsername("");
      setEmail("");
      setProfile("member");

      await loadUsers(selectedOrganizationId);
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Could not create the user."
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  const selectedOrganization = organizations.find(
    (organization) => organization.recordId === selectedOrganizationId
  );

  return (
    <main className="min-h-screen bg-[#f3f0e8] px-6 py-10 text-[#172026]">
      <div className="mx-auto max-w-5xl">
        <h1 className="text-2xl font-bold">User Management</h1>

        <p className="mt-2 text-sm text-[#63717a]">
          Add users to an organization and generate their default password.
        </p>

        {isLoading ? (
          <p className="mt-8 text-sm text-[#63717a]">Loading...</p>
        ) : organizations.length === 0 ? (
          <p className="mt-8 rounded-md border border-[#d6cab8] bg-white p-4 text-sm">
            Create an organization before adding users.
          </p>
        ) : (
          <>
            <section className="mt-8 rounded-lg border border-[#d6cab8] bg-white p-6">
              <h2 className="text-lg font-semibold">Add a user</h2>

              <form
                onSubmit={handleSubmit}
                className="mt-4 grid gap-4 sm:grid-cols-2"
              >
                <label className="block sm:col-span-2">
                  <span className="text-sm font-semibold">Organization</span>

                  <select
                    className="mt-1 h-11 w-full rounded-md border border-[#cfc4b3] bg-white px-3 text-sm"
                    value={selectedOrganizationId}
                    onChange={(event) =>
                      setSelectedOrganizationId(event.target.value)
                    }
                    required
                  >
                    {organizations.map((organization) => (
                      <option
                        key={organization.recordId}
                        value={organization.recordId}
                      >
                        {organization.name}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block">
                  <span className="text-sm font-semibold">Username</span>

                  <input
                    className="mt-1 h-11 w-full rounded-md border border-[#cfc4b3] px-3 text-sm"
                    value={username}
                    onChange={(event) => setUsername(event.target.value)}
                    maxLength={100}
                    autoComplete="off"
                    required
                  />
                </label>

                <label className="block">
                  <span className="text-sm font-semibold">Email</span>

                  <input
                    className="mt-1 h-11 w-full rounded-md border border-[#cfc4b3] px-3 text-sm"
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    maxLength={255}
                    required
                  />
                </label>

                <label className="block sm:col-span-2">
                  <span className="text-sm font-semibold">Profile</span>

                  <select
                    className="mt-1 h-11 w-full rounded-md border border-[#cfc4b3] bg-white px-3 text-sm"
                    value={profile}
                    onChange={(event) => setProfile(event.target.value)}
                  >
                    <option value="member">Member</option>
                    <option value="organization_admin">
                      Organization Admin
                    </option>
                  </select>
                </label>

                {error ? (
                  <p className="rounded-md border border-[#d38b7d] bg-[#fff3f0] px-4 py-3 text-sm text-[#8f2d1f] sm:col-span-2">
                    {error}
                  </p>
                ) : null}

                {defaultPassword ? (
                  <div className="rounded-md border border-[#9cc4b4] bg-[#f4faf7] px-4 py-3 text-sm sm:col-span-2">
                    <p className="font-semibold text-[#1e3a3a]">
                      User created successfully
                    </p>

                    <p className="mt-2">
                      Default password:{" "}
                      <code className="rounded bg-white px-2 py-1 font-mono font-bold">
                        {defaultPassword}
                      </code>
                    </p>

                    <p className="mt-2 text-xs text-[#63717a]">
                      Copy this password now. It will not be shown again.
                    </p>
                  </div>
                ) : null}

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="h-11 rounded-md bg-[#1e3a3a] px-5 text-sm font-semibold text-white disabled:bg-[#9aa7a7] sm:col-span-2 sm:justify-self-start"
                >
                  {isSubmitting ? "Creating..." : "Add user"}
                </button>
              </form>
            </section>

            <section className="mt-8">
              <div className="flex items-end justify-between gap-4">
                <h2 className="text-lg font-semibold">
                  Users in {selectedOrganization?.name}
                </h2>

                {selectedOrganization ? (
                  <p className="text-sm text-[#63717a]">
                    {users.length} / {selectedOrganization.memberLimit} used
                  </p>
                ) : null}
              </div>

              {users.length === 0 ? (
                <p className="mt-3 text-sm text-[#63717a]">
                  No users in this organization.
                </p>
              ) : (
                <div className="mt-3 overflow-x-auto">
                  <table className="w-full border-collapse bg-white text-sm">
                    <thead>
                      <tr className="border-b border-[#d6cab8] text-left text-[#63717a]">
                        <th className="p-3 font-semibold">Username</th>
                        <th className="p-3 font-semibold">Email</th>
                        <th className="p-3 font-semibold">Profile</th>
                        <th className="p-3 font-semibold">Status</th>
                      </tr>
                    </thead>

                    <tbody>
                      {users.map((user) => (
                        <tr
                          key={user.recordId}
                          className="border-b border-[#eae3d7]"
                        >
                          <td className="p-3 font-medium">{user.username}</td>
                          <td className="p-3">{user.email}</td>
                          <td className="p-3">
                            {user.profile === "organization_admin"
                              ? "Organization Admin"
                              : "Member"}
                          </td>
                          <td className="p-3">
                            {user.active ? "Active" : "Inactive"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          </>
        )}
      </div>
    </main>
  );
}