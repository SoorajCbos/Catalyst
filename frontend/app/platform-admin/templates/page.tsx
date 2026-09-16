"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

type Template = {
  recordId: string;
  name: string;
  subject: string;
  body: string;
  allowedMergeFields: string[];
  active: boolean;
};

const MERGE_FIELDS = [
  "{{username}}",
  "{{email}}",
  "{{organization_name}}",
  "{{default_password}}",
];

const SAMPLE_VALUES: Record<string, string> = {
  "{{username}}": "yuvraj_test",
  "{{email}}": "yuvraj@cbosit.com",
  "{{organization_name}}": "CBOS IT",
  "{{default_password}}": "ExamplePass123",
};

const DEFAULT_SUBJECT = "Welcome to {{organization_name}}";

const DEFAULT_BODY =
  "Hello {{username}},\n\n" +
  "Your account for {{organization_name}} is ready.\n\n" +
  "Email: {{email}}\n" +
  "Default password: {{default_password}}\n\n" +
  "Please change your password after signing in.";

function applyMergeFields(text: string): string {
  // Replace known merge fields with sample values for the preview.
  return MERGE_FIELDS.reduce(
    (result, field) => result.replaceAll(field, SAMPLE_VALUES[field]),
    text
  );
}

export default function TemplatePage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);

  const [templateName, setTemplateName] = useState("");
  const [subject, setSubject] = useState(DEFAULT_SUBJECT);
  const [body, setBody] = useState(DEFAULT_BODY);

  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const loadTemplates = useCallback(async () => {
    try {
      setError("");

      const response = await fetch("/api/v1/templates");

      if (!response.ok) {
        throw new Error("Could not load templates.");
      }

      setTemplates((await response.json()) as Template[]);
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Could not load templates."
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadTemplates();
  }, [loadTemplates]);

  function resetEditor() {
    // Return the editor to its initial create-template state.
    setEditingId(null);
    setTemplateName("");
    setSubject(DEFAULT_SUBJECT);
    setBody(DEFAULT_BODY);
    setError("");
    setMessage("");
  }

  function editTemplate(template: Template) {
    // Fill the editor with the selected template.
    setEditingId(template.recordId);
    setTemplateName(template.name);
    setSubject(template.subject);
    setBody(template.body);
    setError("");
    setMessage("");
  }

  function insertMergeField(field: string) {
    // Add spacing when appending a merge field to existing text.
    setBody((currentBody) => {
      const separator =
        currentBody.length > 0 &&
        !currentBody.endsWith(" ") &&
        !currentBody.endsWith("\n")
          ? " "
          : "";

      return `${currentBody}${separator}${field}`;
    });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setError("");
    setMessage("");
    setIsSaving(true);

    try {
      // Editing uses PUT; creating uses POST.
      const url = editingId
        ? `/api/v1/templates/${editingId}`
        : "/api/v1/templates";

      const response = await fetch(url, {
        method: editingId ? "PUT" : "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: templateName.trim(),
          subject: subject.trim(),
          body: body.trim(),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail ?? "Could not save the template.");
      }

      setMessage(
        editingId
          ? "Template updated successfully."
          : "Template created successfully."
      );

      await loadTemplates();

      // Keep an edited template open, but clear the editor after creation.
      if (!editingId) {
        setTemplateName("");
        setSubject(DEFAULT_SUBJECT);
        setBody(DEFAULT_BODY);
      }
    } catch (saveError) {
      setError(
        saveError instanceof Error
          ? saveError.message
          : "Could not save the template."
      );
    } finally {
      setIsSaving(false);
    }
  }

  async function toggleTemplate(template: Template) {
    setError("");
    setMessage("");

    try {
      const response = await fetch(
        `/api/v1/templates/${template.recordId}/status`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            active: !template.active,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ?? "Could not update the template status."
        );
      }

      setMessage(
        template.active
          ? "Template disabled."
          : "Template enabled."
      );

      await loadTemplates();
    } catch (statusError) {
      setError(
        statusError instanceof Error
          ? statusError.message
          : "Could not update the template status."
      );
    }
  }

  return (
    <main className="min-h-screen bg-[#f3f0e8] px-6 py-10 text-[#172026]">
      <div className="mx-auto max-w-7xl">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold">Template Management</h1>

            <p className="mt-2 text-sm text-[#63717a]">
              Create, preview and manage reusable templates.
            </p>
          </div>

          <button
            type="button"
            onClick={resetEditor}
            className="rounded-md border border-[#1e3a3a] px-4 py-2 text-sm font-semibold text-[#1e3a3a]"
          >
            New template
          </button>
        </div>

        {error ? (
          <p className="mt-6 rounded-md border border-[#d38b7d] bg-[#fff3f0] px-4 py-3 text-sm text-[#8f2d1f]">
            {error}
          </p>
        ) : null}

        {message ? (
          <p className="mt-6 rounded-md border border-[#9cc4b4] bg-[#f4faf7] px-4 py-3 text-sm text-[#1e3a3a]">
            {message}
          </p>
        ) : null}

        <div className="mt-8 grid gap-6 xl:grid-cols-[280px_1fr_1fr]">
          <section className="rounded-lg border border-[#d6cab8] bg-white p-5">
            <h2 className="text-lg font-semibold">Saved templates</h2>

            {isLoading ? (
              <p className="mt-4 text-sm text-[#63717a]">Loading...</p>
            ) : templates.length === 0 ? (
              <p className="mt-4 text-sm text-[#63717a]">
                No templates have been created.
              </p>
            ) : (
              <div className="mt-4 space-y-3">
                {templates.map((template) => (
                  <div
                    key={template.recordId}
                    className="rounded-md border border-[#e2dacd] p-3"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="font-semibold">{template.name}</p>

                        <p className="mt-1 text-xs text-[#63717a]">
                          {template.active ? "Active" : "Disabled"}
                        </p>
                      </div>

                      <span
                        className={`h-2.5 w-2.5 rounded-full ${
                          template.active
                            ? "bg-emerald-600"
                            : "bg-zinc-400"
                        }`}
                      />
                    </div>

                    <div className="mt-3 flex gap-2">
                      <button
                        type="button"
                        onClick={() => editTemplate(template)}
                        className="rounded border border-[#cfc4b3] px-3 py-1.5 text-xs font-semibold"
                      >
                        Edit
                      </button>

                      <button
                        type="button"
                        onClick={() => void toggleTemplate(template)}
                        className="rounded border border-[#cfc4b3] px-3 py-1.5 text-xs font-semibold"
                      >
                        {template.active ? "Disable" : "Enable"}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="rounded-lg border border-[#d6cab8] bg-white p-6">
            <h2 className="text-lg font-semibold">
              {editingId ? "Edit template" : "Create template"}
            </h2>

            <form onSubmit={handleSubmit} className="mt-5 space-y-4">
              <label className="block">
                <span className="text-sm font-semibold">Template name</span>

                <input
                  className="mt-1 h-11 w-full rounded-md border border-[#cfc4b3] px-3 text-sm"
                  value={templateName}
                  onChange={(event) =>
                    setTemplateName(event.target.value)
                  }
                  maxLength={100}
                  placeholder="New user welcome"
                  required
                />
              </label>

              <label className="block">
                <span className="text-sm font-semibold">Subject</span>

                <input
                  className="mt-1 h-11 w-full rounded-md border border-[#cfc4b3] px-3 text-sm"
                  value={subject}
                  onChange={(event) => setSubject(event.target.value)}
                  maxLength={200}
                  required
                />
              </label>

              <div>
                <p className="text-sm font-semibold">Merge fields</p>

                <div className="mt-2 flex flex-wrap gap-2">
                  {MERGE_FIELDS.map((field) => (
                    <button
                      key={field}
                      type="button"
                      onClick={() => insertMergeField(field)}
                      className="rounded-md border border-[#cfc4b3] bg-[#fffdf8] px-3 py-2 font-mono text-xs"
                    >
                      {field}
                    </button>
                  ))}
                </div>
              </div>

              <label className="block">
                <span className="text-sm font-semibold">Message body</span>

                <textarea
                  className="mt-1 min-h-64 w-full rounded-md border border-[#cfc4b3] px-3 py-3 text-sm"
                  value={body}
                  onChange={(event) => setBody(event.target.value)}
                  maxLength={10_000}
                  required
                />
              </label>

              <button
                type="submit"
                disabled={isSaving}
                className="rounded-md bg-[#1e3a3a] px-5 py-3 text-sm font-semibold text-white disabled:bg-[#9aa7a7]"
              >
                {isSaving
                  ? "Saving..."
                  : editingId
                    ? "Update template"
                    : "Create template"}
              </button>
            </form>
          </section>

          <section className="rounded-lg border border-[#d6cab8] bg-white p-6">
            <h2 className="text-lg font-semibold">Preview</h2>

            <div className="mt-5 rounded-md border border-[#e2dacd] bg-[#fffdf8] p-5">
              <p className="text-xs font-semibold uppercase tracking-wide text-[#63717a]">
                Subject
              </p>

              <p className="mt-2 font-semibold">
                {applyMergeFields(subject)}
              </p>

              <hr className="my-5 border-[#e2dacd]" />

              <p className="whitespace-pre-wrap text-sm leading-6">
                {applyMergeFields(body)}
              </p>
            </div>

            <p className="mt-4 text-xs leading-5 text-[#63717a]">
              Preview values are examples. Real user and organization data
              will replace these fields when the template is used.
            </p>
          </section>
        </div>
      </div>
    </main>
  );
}