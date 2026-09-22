"use client";

import { ReactNode, useEffect, useState } from "react";
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

type PlatformAdminLayoutProps = {
  children: ReactNode;
};

export default function PlatformAdminLayout({
  children,
}: PlatformAdminLayoutProps) {
  const router = useRouter();

  const [currentUser, setCurrentUser] =
    useState<CurrentUser | null>(null);
  const [isChecking, setIsChecking] = useState(true);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  useEffect(() => {
    async function checkAccess() {
      try {
        // The browser automatically sends the HTTP-only JWT cookie.
        const response = await fetch("/api/v1/auth/me");

        if (!response.ok) {
          router.replace("/");
          return;
        }

        const user = (await response.json()) as CurrentUser;

        // Users with generated passwords must change them first.
        if (user.mustChangePassword) {
          router.replace("/change-password");
          return;
        }

        if (user.profile !== "platform_admin") {
          router.replace("/");
          return;
        }

        setCurrentUser(user);
      } catch {
        router.replace("/");
      } finally {
        setIsChecking(false);
      }
    }

    void checkAccess();
  }, [router]);

  async function handleLogout() {
    setIsLoggingOut(true);

    try {
      // The backend removes the HTTP-only JWT cookie.
      await fetch("/api/v1/auth/logout", {
        method: "POST",
      });
    } finally {
      router.replace("/");
      router.refresh();
    }
  }

  if (isChecking) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#f3f0e8]">
        <p className="text-sm text-[#63717a]">
          Checking access...
        </p>
      </main>
    );
  }

  if (!currentUser) {
    return null;
  }

  return (
    <div className="min-h-screen bg-[#f3f0e8] text-[#172026]">
      <header className="border-b border-[#d6cab8] bg-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-6 py-4">
          <div>
            <p className="font-bold">
              Platform Administration
            </p>

            <p className="text-xs text-[#63717a]">
              Signed in as {currentUser.username}
            </p>
          </div>

          <nav className="flex flex-wrap items-center gap-4 text-sm font-semibold">
            <a
              href="/platform-admin/home"
              className="hover:underline"
            >
              Home
            </a>

            <a
              href="/platform-admin"
              className="hover:underline"
            >
              Organizations
            </a>

            <a
              href="/platform-admin/users"
              className="hover:underline"
            >
              Users
            </a>

            <a
              href="/platform-admin/templates"
              className="hover:underline"
            >
              Templates
            </a>

            <a
              href="/platform-admin/agent"
              className="hover:underline"
            >
              Agent
            </a>

            <button
              type="button"
              onClick={handleLogout}
              disabled={isLoggingOut}
              className="rounded-md bg-[#1e3a3a] px-4 py-2 text-white disabled:bg-[#9aa7a7]"
            >
              {isLoggingOut
                ? "Signing out..."
                : "Sign out"}
            </button>
          </nav>
        </div>
      </header>

      {children}
    </div>
  );
}
      