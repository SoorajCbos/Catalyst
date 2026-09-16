"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";

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

type GuideType = "main" | "profile" | "role";

type Guide = {
  recordId: string;
  organizationId: string;
  title: string;
  guideType: GuideType;
  audience: string;
  fileName: string;
  filePath: string;
  content: string;
  updatedAt: string;
};

type GuideForm = {
  title: string;
  guideType: GuideType;
  audience: string;
  content: string;
};

const EMPTY_GUIDE: GuideForm = {
  title: "",
  guideType: "main",
  audience: "All users",
  content: "# Organization access guide\n\n## Permissions\n\n",
};

async function readError(response: Response, fallback: string) {
  const data = await response.json().catch(() => ({}));
  return data.detail ?? fallback;
}

export default function OrganizationDetailPage() {
  const params = useParams<{ organizationId: string }>();
  const organizationId = params.organizationId;
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [guides, setGuides] = useState<Guide[]>([]);
  const [guideForm, setGuideForm] = useState<GuideForm>(EMPTY_GUIDE);
  const [editingGuideId, setEditingGuideId] = useState<string | null>(null);
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [profile, setProfile] = useState("member");
  const [defaultPassword, setDefaultPassword] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSavingUser, setIsSavingUser] = useState(false);
  const [isSavingGuide, setIsSavingGuide] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const loadOrganizationData = useCallback(async () => {
    setError("");

    const [organizationsResponse, usersResponse, guidesResponse] = await Promise.all([
      fetch("/api/v1/organizations"),
      fetch(`/api/v1/users?organizationId=${encodeURIComponent(organizationId)}`),
      fetch(`/api/v1/organization-guides?organization_id=${encodeURIComponent(organizationId)}`),
    ]);

    if (!organizationsResponse.ok) {
      throw new Error(await readError(organizationsResponse, "Could not load organizations."));
    }
    if (!usersResponse.ok) {
      throw new Error(await readError(usersResponse, "Could not load users."));
    }
    if (!guidesResponse.ok) {
      throw new Error(await readError(guidesResponse, "Could not load permission guides."));
    }

    const organizations = (await organizationsResponse.json()) as Organization[];
    setOrganization(organizations.find((item) => item.recordId === organizationId) ?? null);
    setUsers((await usersResponse.json()) as User[]);
    setGuides((await guidesResponse.json()) as Guide[]);
  }, [organizationId]);

  useEffect(() => {
    async function loadPage() {
      try {
        await loadOrganizationData();
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Could not load organization.");
      } finally {
        setIsLoading(false);
      }
    }

    void loadPage();
  }, [loadOrganizationData]);

  async function handleUserSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    setDefaultPassword("");
    setIsSavingUser(true);

    try {
      const response = await fetch("/api/v1/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: username.trim(),
          email: email.trim(),
          organizationId,
          profile,
        }),
      });
      if (!response.ok) {
        throw new Error(await readError(response, "Could not create the user."));
      }

      const createdUser = (await response.json()) as { defaultPassword: string };
      setDefaultPassword(createdUser.defaultPassword);
      setUsername("");
      setEmail("");
      setProfile("member");
      setMessage("User added to this organization.");
      await loadOrganizationData();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Could not create the user.");
    } finally {
      setIsSavingUser(false);
    }
  }

  function editGuide(guide: Guide) {
    setEditingGuideId(guide.recordId);
    setGuideForm({
      title: guide.title,
      guideType: guide.guideType,
      audience: guide.audience,
      content: guide.content,
    });
    setMessage("");
    setError("");
  }

  function startNewGuide() {
    setEditingGuideId(null);
    setGuideForm(EMPTY_GUIDE);
    setMessage("");
    setError("");
  }

  async function handleGuideSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    setIsSavingGuide(true);

    try {
      const response = await fetch(
        editingGuideId
          ? `/api/v1/organization-guides/${editingGuideId}`
          : "/api/v1/organization-guides",
        {
          method: editingGuideId ? "PUT" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ organizationId, ...guideForm }),
        }
      );
      if (!response.ok) {
        throw new Error(await readError(response, "Could not save the guide."));
      }

      setMessage(editingGuideId ? "Permission guide updated." : "Permission guide saved as Markdown.");
      await loadOrganizationData();
      setEditingGuideId(null);
      setGuideForm(EMPTY_GUIDE);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Could not save the guide.");
    } finally {
      setIsSavingGuide(false);
    }
  }

  if (isLoading) {
    return <main className="min-h-screen bg-[#f3f0e8] px-6 py-10 text-sm text-[#63717a]">Loading organization...</main>;
  }

  if (!organization) {
    return (
      <main className="min-h-screen bg-[#f3f0e8] px-6 py-10 text-[#172026]">
        <p className="rounded-md border border-[#d38b7d] bg-[#fff3f0] p-4 text-sm text-[#8f2d1f]">{error || "Organization not found."}</p>
        <Link href="/platform-admin" className="mt-5 inline-block text-sm font-semibold underline">Back to organizations</Link>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#f3f0e8] px-6 py-10 text-[#172026]">
      <div className="mx-auto max-w-7xl">
        <Link href="/platform-admin" className="text-sm font-semibold text-[#1e3a3a] hover:underline">← Back to organizations</Link>
        <div className="mt-5 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#7c4d2c]">Organization workspace</p>
            <h1 className="mt-2 text-3xl font-bold">{organization.name}</h1>
            <p className="mt-2 text-sm text-[#63717a]">Tier: {organization.tier} · {users.length} / {organization.memberLimit} members</p>
          </div>
          <div className="rounded-md border border-[#d6cab8] bg-white px-4 py-3 text-sm"><span className="font-semibold">Organization ID:</span> {organization.recordId}</div>
        </div>

        {error ? <p className="mt-6 rounded-md border border-[#d38b7d] bg-[#fff3f0] px-4 py-3 text-sm text-[#8f2d1f]">{error}</p> : null}
        {message ? <p className="mt-6 rounded-md border border-[#9cc4b4] bg-[#f4faf7] px-4 py-3 text-sm text-[#1e3a3a]">{message}</p> : null}

        <section className="mt-8 rounded-lg border border-[#d6cab8] bg-white p-6">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div><h2 className="text-xl font-bold">Users in {organization.name}</h2><p className="mt-1 text-sm text-[#63717a]">Review existing users or add a new user to this organization.</p></div>
            <span className="text-sm text-[#63717a]">{users.length} / {organization.memberLimit} used</span>
          </div>
          <div className="mt-5 overflow-x-auto">
            {users.length === 0 ? <p className="text-sm text-[#63717a]">No users in this organization.</p> : <table className="w-full border-collapse text-sm"><thead><tr className="border-b border-[#d6cab8] text-left text-[#63717a]"><th className="p-3 font-semibold">Username</th><th className="p-3 font-semibold">Email</th><th className="p-3 font-semibold">Profile</th><th className="p-3 font-semibold">Status</th></tr></thead><tbody>{users.map((user) => <tr key={user.recordId} className="border-b border-[#eae3d7]"><td className="p-3 font-medium">{user.username}</td><td className="p-3">{user.email}</td><td className="p-3">{user.profile === "organization_admin" ? "Organization Admin" : "Member"}</td><td className="p-3">{user.active ? "Active" : "Inactive"}</td></tr>)}</tbody></table>}
          </div>
          <form onSubmit={handleUserSubmit} className="mt-6 grid gap-4 border-t border-[#eae3d7] pt-6 sm:grid-cols-2">
            <h3 className="text-lg font-semibold sm:col-span-2">Add user to {organization.name}</h3>
            <label className="block"><span className="text-sm font-semibold">Username</span><input required maxLength={100} value={username} onChange={(event) => setUsername(event.target.value)} className="mt-1 h-11 w-full rounded-md border border-[#cfc4b3] px-3 text-sm" /></label>
            <label className="block"><span className="text-sm font-semibold">Email</span><input required type="email" maxLength={255} value={email} onChange={(event) => setEmail(event.target.value)} className="mt-1 h-11 w-full rounded-md border border-[#cfc4b3] px-3 text-sm" /></label>
            <label className="block sm:col-span-2"><span className="text-sm font-semibold">Profile</span><select value={profile} onChange={(event) => setProfile(event.target.value)} className="mt-1 h-11 w-full rounded-md border border-[#cfc4b3] bg-white px-3 text-sm"><option value="member">Member</option><option value="organization_admin">Organization Admin</option></select></label>
            {defaultPassword ? <p className="rounded-md border border-[#9cc4b4] bg-[#f4faf7] px-4 py-3 text-sm sm:col-span-2">Default password: <code className="font-bold">{defaultPassword}</code></p> : null}
            <button type="submit" disabled={isSavingUser} className="h-11 rounded-md bg-[#1e3a3a] px-5 text-sm font-semibold text-white disabled:bg-[#9aa7a7] sm:justify-self-start">{isSavingUser ? "Creating..." : "Add user"}</button>
          </form>
        </section>

        <section className="mt-8 rounded-lg border border-[#d6cab8] bg-white p-6">
          <div className="flex flex-wrap items-end justify-between gap-4"><div><h2 className="text-xl font-bold">Permission guides</h2><p className="mt-1 text-sm text-[#63717a]">View files already added for {organization.name} or create another Markdown guide.</p></div><button type="button" onClick={startNewGuide} className="rounded-md border border-[#1e3a3a] px-4 py-2 text-sm font-semibold text-[#1e3a3a]">New guide</button></div>
          <div className="mt-5 grid gap-6 lg:grid-cols-[300px_1fr]">
            <div className="space-y-3">{guides.length === 0 ? <p className="text-sm text-[#63717a]">No permission guides saved yet.</p> : guides.map((guide) => <button key={guide.recordId} type="button" onClick={() => editGuide(guide)} className={`w-full rounded-md border p-3 text-left ${editingGuideId === guide.recordId ? "border-[#1e3a3a] bg-[#f4faf7]" : "border-[#e2dacd]"}`}><p className="font-semibold">{guide.title}</p><p className="mt-1 text-xs text-[#63717a]">{guide.guideType} · {guide.audience}</p><p className="mt-2 text-xs text-[#63717a]">{guide.fileName}</p></button>)}</div>
            <form onSubmit={handleGuideSubmit} className="space-y-4 border-t border-[#eae3d7] pt-5 lg:border-l lg:border-t-0 lg:pl-6 lg:pt-0"><h3 className="text-lg font-semibold">{editingGuideId ? "Edit Markdown guide" : "Add permission guide"}</h3><label className="block"><span className="text-sm font-semibold">Guide title</span><input required value={guideForm.title} onChange={(event) => setGuideForm((current) => ({ ...current, title: event.target.value }))} className="mt-1 h-11 w-full rounded-md border border-[#cfc4b3] px-3 text-sm" placeholder="Organization access guide" /></label><div className="grid gap-4 sm:grid-cols-2"><label className="block"><span className="text-sm font-semibold">Guide type</span><select value={guideForm.guideType} onChange={(event) => setGuideForm((current) => ({ ...current, guideType: event.target.value as GuideType }))} className="mt-1 h-11 w-full rounded-md border border-[#cfc4b3] bg-white px-3 text-sm"><option value="main">Main reference</option><option value="profile">Profile guide</option><option value="role">Role guide</option></select></label><label className="block"><span className="text-sm font-semibold">Profile or role</span><input required value={guideForm.audience} onChange={(event) => setGuideForm((current) => ({ ...current, audience: event.target.value }))} className="mt-1 h-11 w-full rounded-md border border-[#cfc4b3] px-3 text-sm" /></label></div><label className="block"><span className="text-sm font-semibold">Markdown content</span><textarea required value={guideForm.content} onChange={(event) => setGuideForm((current) => ({ ...current, content: event.target.value }))} className="mt-2 min-h-[360px] w-full resize-y rounded-md border border-[#cfc4b3] bg-[#fffdf8] p-4 font-mono text-sm leading-6 outline-none focus:border-[#9a6a43]" /></label><button type="submit" disabled={isSavingGuide} className="h-11 rounded-md bg-[#1e3a3a] px-5 text-sm font-semibold text-white disabled:bg-[#9aa7a7]">{isSavingGuide ? "Saving..." : editingGuideId ? "Save changes" : "Save as .md"}</button></form>
          </div>
        </section>
      </div>
    </main>
  );
}