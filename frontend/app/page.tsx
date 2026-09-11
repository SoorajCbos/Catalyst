"use client";

import { FormEvent, useState } from "react";

type UserProfile = "platform_admin" | "organization_admin" | "member";

type UserRecord = {
  recordId: string;
  username: string;
  email: string;
  organizationId: string;
  active: boolean;
  profile: UserProfile;
};

type LoginResponse = {
  user: UserRecord;
  entryPoint: string;
  organizationTier?: string;
  organizationMemberLimit?: number;
};

const profileLabels: Record<UserProfile, string> = {
  platform_admin: "Platform Admin",
  organization_admin: "Organization Admin",
  member: "Member",
};

async function loginWithBackend(username: string, password: string) {
  const response = await fetch("/api/v1/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) {
    throw new Error("Login failed. Check the username, password, or active status.");
  }

  return (await response.json()) as LoginResponse;
}

function getEntryDescription(profile: UserProfile) {
  if (profile === "platform_admin") {
    return "Open the platform administration page for organizations, users, and purchased tiers.";
  }

  if (profile === "organization_admin") {
    return "Open the organization administration page for adding members within the assigned member limit.";
  }

  return "Open the normal application interface.";
}

export default function Home() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loginResult, setLoginResult] = useState<LoginResponse | null>(null);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoginResult(null);
    setIsSubmitting(true);

    try {
      const result = await loginWithBackend(username.trim(), password);
      setLoginResult(result);
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : "Login failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#f3f0e8] px-5 py-6 text-[#1f2933] sm:px-8 lg:px-12">
      <section className="mx-auto grid min-h-[calc(100vh-3rem)] max-w-6xl gap-8 lg:grid-cols-[1fr_440px] lg:items-center">
        <div className="space-y-8">
          <div className="max-w-2xl space-y-5">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#7c4d2c]">
              Central Access
            </p>
            <h1 className="text-4xl font-bold leading-tight text-[#172026] sm:text-5xl">
              One login directs every user to the correct organization workspace.
            </h1>
            <p className="max-w-xl text-base leading-7 text-[#52616b] sm:text-lg">
              The backend checks the user table by username, validates the password, confirms active status, and returns the user profile used for routing.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            {(["platform_admin", "organization_admin", "member"] as UserProfile[]).map((profile) => (
              <div key={profile} className="rounded-lg border border-[#d8cfbf] bg-white/70 p-4 shadow-sm">
                <p className="text-sm font-semibold text-[#172026]">{profileLabels[profile]}</p>
                <p className="mt-2 text-sm leading-6 text-[#63717a]">{getEntryDescription(profile)}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-[#d6cab8] bg-white p-6 shadow-[0_24px_80px_rgba(54,41,24,0.14)]">
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-[#172026]">Sign in</h2>
            <p className="mt-2 text-sm leading-6 text-[#63717a]">
              Use the unique username assigned in the user table.
            </p>
          </div>

          <form className="space-y-4" onSubmit={handleSubmit}>
            <label className="block">
              <span className="text-sm font-semibold text-[#26323a]">Username</span>
              <input
                className="mt-2 h-12 w-full rounded-md border border-[#cfc4b3] bg-[#fffdf8] px-4 text-base outline-none transition focus:border-[#9a6a43] focus:ring-4 focus:ring-[#9a6a43]/15"
                name="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                autoComplete="username"
                required
              />
            </label>

            <label className="block">
              <span className="text-sm font-semibold text-[#26323a]">Password</span>
              <input
                className="mt-2 h-12 w-full rounded-md border border-[#cfc4b3] bg-[#fffdf8] px-4 text-base outline-none transition focus:border-[#9a6a43] focus:ring-4 focus:ring-[#9a6a43]/15"
                name="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                required
              />
            </label>

            {error ? (
              <p className="rounded-md border border-[#d38b7d] bg-[#fff3f0] px-4 py-3 text-sm text-[#8f2d1f]">
                {error}
              </p>
            ) : null}

            <button
              className="h-12 w-full rounded-md bg-[#1e3a3a] px-5 text-base font-semibold text-white transition hover:bg-[#285050] disabled:cursor-not-allowed disabled:bg-[#9aa7a7]"
              disabled={isSubmitting}
              type="submit"
            >
              {isSubmitting ? "Checking user table..." : "Continue"}
            </button>
          </form>

          {loginResult ? (
            <div className="mt-6 rounded-lg border border-[#cbd7d3] bg-[#f4faf7] p-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-semibold text-[#1e3a3a]">Authenticated user</p>
                  <p className="mt-1 text-lg font-bold text-[#172026]">{loginResult.user.username}</p>
                </div>
                <span className="rounded-md bg-[#dceee7] px-3 py-1 text-xs font-bold uppercase tracking-[0.12em] text-[#1e3a3a]">
                  {profileLabels[loginResult.user.profile]}
                </span>
              </div>

              <dl className="mt-4 grid gap-3 text-sm">
                <div className="flex justify-between gap-4">
                  <dt className="text-[#63717a]">Record ID</dt>
                  <dd className="font-semibold text-[#26323a]">{loginResult.user.recordId}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-[#63717a]">Email</dt>
                  <dd className="font-semibold text-[#26323a]">{loginResult.user.email}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-[#63717a]">Organization ID</dt>
                  <dd className="font-semibold text-[#26323a]">{loginResult.user.organizationId}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-[#63717a]">Status</dt>
                  <dd className="font-semibold text-[#26323a]">
                    {loginResult.user.active ? "Active" : "Inactive"}
                  </dd>
                </div>
              </dl>

              <div className="mt-4 rounded-md bg-white px-4 py-3 text-sm leading-6 text-[#40505a]">
                Next entry point: <span className="font-semibold text-[#172026]">{loginResult.entryPoint}</span>
              </div>
            </div>
          ) : null}
        </div>
      </section>
    </main>
  );
}
