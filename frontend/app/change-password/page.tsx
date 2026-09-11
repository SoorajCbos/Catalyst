"use client";

import { FormEvent, useState } from "react";

export default function ChangePasswordPage() {
  const [username, setUsername] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    // Prevent the browser from reloading the page when the form submits.
    event.preventDefault();

    setError("");
    setMessage("");

    if (newPassword !== confirmPassword) {
      setError("New passwords do not match.");
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await fetch("/api/v1/auth/change-password", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: username.trim(),
          currentPassword,
          newPassword,
          confirmPassword,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        // FastAPI returns readable error messages in the detail property.
        throw new Error(data.detail ?? "Could not change the password.");
      }

      setMessage(data.message);

      // Clear password fields after a successful change.
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Could not change the password."
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#f3f0e8] px-6 py-10 text-[#172026]">
      <div className="mx-auto max-w-md">
        <section className="rounded-lg border border-[#d6cab8] bg-white p-6 shadow-sm">
          <h1 className="text-2xl font-bold">Change Password</h1>

          <p className="mt-2 text-sm leading-6 text-[#63717a]">
            Enter your username, current password and new password.
          </p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <label className="block">
              <span className="text-sm font-semibold">Username</span>

              <input
                className="mt-1 h-11 w-full rounded-md border border-[#cfc4b3] px-3 text-sm"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                maxLength={100}
                autoComplete="username"
                required
              />
            </label>

            <label className="block">
              <span className="text-sm font-semibold">Current password</span>

              <input
                className="mt-1 h-11 w-full rounded-md border border-[#cfc4b3] px-3 text-sm"
                type="password"
                value={currentPassword}
                onChange={(event) => setCurrentPassword(event.target.value)}
                autoComplete="current-password"
                required
              />
            </label>

            <label className="block">
              <span className="text-sm font-semibold">New password</span>

              <input
                className="mt-1 h-11 w-full rounded-md border border-[#cfc4b3] px-3 text-sm"
                type="password"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                minLength={8}
                autoComplete="new-password"
                required
              />

              <span className="mt-1 block text-xs text-[#63717a]">
                Use at least 8 characters.
              </span>
            </label>

            <label className="block">
              <span className="text-sm font-semibold">
                Confirm new password
              </span>

              <input
                className="mt-1 h-11 w-full rounded-md border border-[#cfc4b3] px-3 text-sm"
                type="password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                minLength={8}
                autoComplete="new-password"
                required
              />
            </label>

            {error ? (
              <p className="rounded-md border border-[#d38b7d] bg-[#fff3f0] px-4 py-3 text-sm text-[#8f2d1f]">
                {error}
              </p>
            ) : null}

            {message ? (
              <p className="rounded-md border border-[#9cc4b4] bg-[#f4faf7] px-4 py-3 text-sm text-[#1e3a3a]">
                {message}
              </p>
            ) : null}

            <button
              type="submit"
              disabled={isSubmitting}
              className="h-11 w-full rounded-md bg-[#1e3a3a] px-5 text-sm font-semibold text-white disabled:bg-[#9aa7a7]"
            >
              {isSubmitting ? "Changing password..." : "Change password"}
            </button>
          </form>

          <a
            href="/"
            className="mt-5 block text-center text-sm font-semibold text-[#1e3a3a] hover:underline"
          >
            Back to sign in
          </a>
        </section>
      </div>
    </main>
  );
}