"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type CurrentUser = {
  recordId: string;
  username: string;
  email: string;
  organizationId: string;
  active: boolean;
  profile: string;
  mustChangePassword: boolean;
};

export default function ChangePasswordPage() {
  const router = useRouter();

  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [isChecking, setIsChecking] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    async function loadCurrentUser() {
      try {
        // The backend identifies the user from the HTTP-only JWT cookie.
        const response = await fetch("/api/v1/auth/me");

        if (!response.ok) {
          router.replace("/");
          return;
        }

        setCurrentUser((await response.json()) as CurrentUser);
      } catch {
        router.replace("/");
      } finally {
        setIsChecking(false);
      }
    }

    void loadCurrentUser();
  }, [router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
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
        // Username is not sent. The backend gets the user's identity from
        // the verified JWT session.
        body: JSON.stringify({
          currentPassword,
          newPassword,
          confirmPassword,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail ?? "Could not change the password.");
      }

      setMessage(data.message);

      // End the old session so the user verifies the new password by
      // signing in again.
      await fetch("/api/v1/auth/logout", {
        method: "POST",
      });

      window.setTimeout(() => {
        router.replace("/");
        router.refresh();
      }, 1000);
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

  if (isChecking) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#f3f0e8]">
        <p className="text-sm text-[#63717a]">Checking session...</p>
      </main>
    );
  }

  if (!currentUser) {
    return null;
  }

  return (
    <main className="min-h-screen bg-[#f3f0e8] px-6 py-10 text-[#172026]">
      <div className="mx-auto max-w-md">
        <section className="rounded-lg border border-[#d6cab8] bg-white p-6 shadow-sm">
          <h1 className="text-2xl font-bold">Change Password</h1>

          <p className="mt-2 text-sm leading-6 text-[#63717a]">
            Signed in as{" "}
            <span className="font-semibold">{currentUser.username}</span>
          </p>

          {currentUser.mustChangePassword ? (
            <p className="mt-4 rounded-md border border-[#d9b96e] bg-[#fff9e8] px-4 py-3 text-sm text-[#72551a]">
              You must replace your generated default password before
              continuing.
            </p>
          ) : null}

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <label className="block">
              <span className="text-sm font-semibold">
                Current password
              </span>

              <input
                className="mt-1 h-11 w-full rounded-md border border-[#cfc4b3] px-3 text-sm"
                type="password"
                value={currentPassword}
                onChange={(event) =>
                  setCurrentPassword(event.target.value)
                }
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
                onChange={(event) =>
                  setConfirmPassword(event.target.value)
                }
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
                {message} Returning to sign in...
              </p>
            ) : null}

            <button
              type="submit"
              disabled={isSubmitting}
              className="h-11 w-full rounded-md bg-[#1e3a3a] px-5 text-sm font-semibold text-white disabled:bg-[#9aa7a7]"
            >
              {isSubmitting
                ? "Changing password..."
                : "Change password"}
            </button>
          </form>
        </section>
      </div>
    </main>
  );
}