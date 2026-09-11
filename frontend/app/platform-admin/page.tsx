"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

type Organization = {
  recordId: string;
  name: string;
  tier: string;
  memberLimit: number;
};

// The login response sends users here when their profile is platform_admin.
// This page covers the first of the three things that entry point is for:
// adding organizations and assigning their purchased tier.
export default function PlatformAdminPage() {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [name, setName] = useState("");
  const [tier, setTier] = useState("");
  const [memberLimit, setMemberLimit] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Wrapped in useCallback so the reference stays stable and it can safely
  // be listed as a dependency of the useEffect below.
  const loadOrganizations = useCallback(async () => {
    setError("");

    try {
      // A relative URL. next.config.ts rewrites /api/v1/* to the backend
      // on port 8000, so the browser sees one address and there is no
      // cross-origin request to configure.
      const response = await fetch("/api/v1/organizations");

      if (!response.ok) {
        throw new Error("Could not load organizations.");
      }

      setOrganizations((await response.json()) as Organization[]);
    } catch (loadError) {
      setError(
        loadError instanceof Error ? loadError.message : "Could not load organizations."
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Runs once when the page first appears, to fill the list.
  useEffect(() => {
    void loadOrganizations();
  }, [loadOrganizations]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    // Without this the browser reloads the page and the result is lost.
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      const response = await fetch("/api/v1/organizations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          tier: tier.trim(),
          // The form value is text; the backend expects a number.
          memberLimit: Number(memberLimit),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        // FastAPI puts its error message in 'detail'.
        throw new Error(data.detail ?? "Could not create the organization.");
      }

      // Clear the form and reload the list so the new row appears.
      setName("");
      setTier("");
      setMemberLimit("");
      await loadOrganizations();
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Could not create the organization."
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <h1 className="text-2xl font-bold text-[#172026]">Platform Administration</h1>
      <p className="mt-2 text-sm text-[#63717a]">
        Add organizations and assign their purchased tier and member limit.
      </p>

      <section className="mt-8 rounded-lg border border-[#d6cab8] bg-white p-6">
        <h2 className="text-lg font-semibold text-[#172026]">Add an organization</h2>

        <form onSubmit={handleSubmit} className="mt-4 grid gap-4 sm:grid-cols-3">
          <label className="block">
            <span className="text-sm font-semibold text-[#26323a]">Name</span>
            <input
              className="mt-1 h-11 w-full rounded-md border border-[#cfc4b3] px-3 text-sm"
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={100}
              required
            />
          </label>

          <label className="block">
            <span className="text-sm font-semibold text-[#26323a]">Tier</span>
            <input
              className="mt-1 h-11 w-full rounded-md border border-[#cfc4b3] px-3 text-sm"
              value={tier}
              onChange={(event) => setTier(event.target.value)}
              maxLength={50}
              required
            />
          </label>

          <label className="block">
            <span className="text-sm font-semibold text-[#26323a]">Member limit</span>
            <input
              className="mt-1 h-11 w-full rounded-md border border-[#cfc4b3] px-3 text-sm"
              type="number"
              min={1}
              value={memberLimit}
              onChange={(event) => setMemberLimit(event.target.value)}
              required
            />
          </label>

          {error ? (
            <p className="rounded-md border border-[#d38b7d] bg-[#fff3f0] px-4 py-3 text-sm text-[#8f2d1f] sm:col-span-3">
              {error}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={isSubmitting}
            className="h-11 rounded-md bg-[#1e3a3a] px-5 text-sm font-semibold text-white disabled:bg-[#9aa7a7] sm:col-span-3 sm:justify-self-start"
          >
            {isSubmitting ? "Saving..." : "Add organization"}
          </button>
        </form>
      </section>

      <section className="mt-8">
        <h2 className="text-lg font-semibold text-[#172026]">Organizations</h2>

        {isLoading ? (
          <p className="mt-3 text-sm text-[#63717a]">Loading...</p>
        ) : organizations.length === 0 ? (
          <p className="mt-3 text-sm text-[#63717a]">No organizations yet.</p>
        ) : (
          <table className="mt-3 w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-[#d6cab8] text-left text-[#63717a]">
                <th className="py-2 font-semibold">Name</th>
                <th className="py-2 font-semibold">Tier</th>
                <th className="py-2 font-semibold">Member limit</th>
              </tr>
            </thead>
            <tbody>
              {organizations.map((organization) => (
                // React needs a stable key per row to track them efficiently.
                <tr key={organization.recordId} className="border-b border-[#eae3d7]">
                  <td className="py-2 font-medium text-[#172026]">{organization.name}</td>
                  <td className="py-2 text-[#40505a]">{organization.tier}</td>
                  <td className="py-2 text-[#40505a]">{organization.memberLimit}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </main>
  );
}