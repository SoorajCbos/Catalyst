"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

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

type Organization = {
  recordId: string;
  name: string;
  tier: string;
};

const EMPTY_GUIDE = {
  organizationId: "",
  title: "",
  guideType: "main" as GuideType,
  audience: "All users",
  content: "# Organization access guide\n\n## Permissions\n\n",
};

export default function OrganizationGuidesPage() {
  const [guides, setGuides] = useState<Guide[]>([]);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState(EMPTY_GUIDE);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const loadGuides = useCallback(async () => {
    try {
      const response = await fetch("/api/v1/organization-guides");
      if (!response.ok) throw new Error("Could not load organization guides.");
      setGuides((await response.json()) as Guide[]);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Could not load guides.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadOrganizations = useCallback(async () => {
    try {
      const response = await fetch("/api/v1/organizations");
      if (!response.ok) throw new Error("Could not load organizations.");
      setOrganizations((await response.json()) as Organization[]);
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Could not load organizations."
      );
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadGuides();
    }, 0);

    return () => window.clearTimeout(timer);
  }, [loadGuides]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadOrganizations();
    }, 0);

    return () => window.clearTimeout(timer);
  }, [loadOrganizations]);

  function updateField(field: keyof typeof EMPTY_GUIDE, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function editGuide(guide: Guide) {
    setEditingId(guide.recordId);
    setForm({
      organizationId: guide.organizationId,
      title: guide.title,
      guideType: guide.guideType,
      audience: guide.audience,
      content: guide.content,
    });
    setMessage("");
    setError("");
  }

  function startNewGuide() {
    setEditingId(null);
    setForm(EMPTY_GUIDE);
    setMessage("");
    setError("");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSaving(true);
    setError("");
    setMessage("");

    try {
      const response = await fetch(
        editingId
          ? `/api/v1/organization-guides/${editingId}`
          : "/api/v1/organization-guides",
        {
          method: editingId ? "PUT" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(form),
        }
      );
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Could not save guide.");

      setMessage(editingId ? "Guide updated and saved as Markdown." : "Guide saved as Markdown.");
      setEditingId(data.recordId);
      await loadGuides();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Could not save guide.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#f3f0e8] px-6 py-10 text-[#172026]">
      <div className="mx-auto max-w-7xl">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold">Organization Permission Guides</h1>
            <p className="mt-2 text-sm text-[#63717a]">
              Write one or more Markdown guides for each organization, profile, or role.
            </p>
          </div>
          <button type="button" onClick={startNewGuide} className="rounded-md border border-[#1e3a3a] px-4 py-2 text-sm font-semibold text-[#1e3a3a]">
            New guide
          </button>
        </div>

        {error ? <p className="mt-5 rounded-md border border-[#d38b7d] bg-[#fff3f0] px-4 py-3 text-sm text-[#8f2d1f]">{error}</p> : null}
        {message ? <p className="mt-5 rounded-md border border-[#9cc4b4] bg-[#f4faf7] px-4 py-3 text-sm text-[#1e3a3a]">{message}</p> : null}

        <div className="mt-8 grid gap-6 lg:grid-cols-[300px_1fr]">
          <section className="rounded-lg border border-[#d6cab8] bg-white p-5">
            <h2 className="text-lg font-semibold">Saved guides</h2>
            {isLoading ? <p className="mt-4 text-sm text-[#63717a]">Loading...</p> : guides.length === 0 ? <p className="mt-4 text-sm text-[#63717a]">No guides saved yet.</p> : (
              <div className="mt-4 space-y-3">
                {guides.map((guide) => (
                  <button key={guide.recordId} type="button" onClick={() => editGuide(guide)} className={`w-full rounded-md border p-3 text-left ${editingId === guide.recordId ? "border-[#1e3a3a] bg-[#f4faf7]" : "border-[#e2dacd]"}`}>
                    <p className="font-semibold">{guide.title}</p>
                    <p className="mt-1 text-xs text-[#63717a]">{guide.organizationId} · {guide.guideType} · {guide.audience}</p>
                    <p className="mt-2 text-xs text-[#63717a]">{guide.fileName}</p>
                  </button>
                ))}
              </div>
            )}
          </section>

          <section className="rounded-lg border border-[#d6cab8] bg-white p-6">
            <h2 className="text-lg font-semibold">{editingId ? "Edit Markdown guide" : "Write Markdown guide"}</h2>
            <form onSubmit={handleSubmit} className="mt-5 space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="block"><span className="text-sm font-semibold">Organization</span><select required value={form.organizationId} onChange={(event) => updateField("organizationId", event.target.value)} className="mt-1 h-11 w-full rounded-md border border-[#cfc4b3] px-3 text-sm"><option value="">Select an organization</option>{organizations.map((organization) => <option key={organization.recordId} value={organization.recordId}>{organization.name} ({organization.recordId})</option>)}</select></label>
                <label className="block"><span className="text-sm font-semibold">Guide title</span><input required value={form.title} onChange={(event) => updateField("title", event.target.value)} className="mt-1 h-11 w-full rounded-md border border-[#cfc4b3] px-3 text-sm" placeholder="Organization access guide" /></label>
                <label className="block"><span className="text-sm font-semibold">Guide type</span><select value={form.guideType} onChange={(event) => updateField("guideType", event.target.value)} className="mt-1 h-11 w-full rounded-md border border-[#cfc4b3] px-3 text-sm"><option value="main">Main reference</option><option value="profile">Profile guide</option><option value="role">Role guide</option></select></label>
                <label className="block"><span className="text-sm font-semibold">Profile or role</span><input required value={form.audience} onChange={(event) => updateField("audience", event.target.value)} className="mt-1 h-11 w-full rounded-md border border-[#cfc4b3] px-3 text-sm" placeholder="All users, member, admin" /></label>
              </div>
              <label className="block"><span className="text-sm font-semibold">Markdown content</span><textarea required value={form.content} onChange={(event) => updateField("content", event.target.value)} className="mt-2 min-h-[420px] w-full resize-y rounded-md border border-[#cfc4b3] bg-[#fffdf8] p-4 font-mono text-sm leading-6 outline-none focus:border-[#9a6a43]" /></label>
              <button type="submit" disabled={isSaving} className="h-11 rounded-md bg-[#1e3a3a] px-5 text-sm font-semibold text-white disabled:bg-[#9aa7a7]">{isSaving ? "Saving..." : editingId ? "Save changes" : "Save as .md"}</button>
            </form>
          </section>
        </div>
      </div>
    </main>
  );
}