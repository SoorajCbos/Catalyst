"use client";

import Link from "next/link";

export default function PlatformAdminHomePage() {
  return (
    <main className="min-h-screen bg-[#f3f0e8] px-6 py-10 text-[#172026]">
      <div className="mx-auto max-w-7xl">
        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#7c4d2c]">
          Platform workspace
        </p>
        <h1 className="mt-3 text-3xl font-bold">Welcome to the admin home</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-[#63717a]">
          Choose an organization to review its users, member limit, and permission guides.
        </p>

        <div className="mt-8 grid gap-5 md:grid-cols-2">
          <Link
            href="/platform-admin"
            className="rounded-lg border border-[#d6cab8] bg-white p-6 transition hover:border-[#1e3a3a]"
          >
            <p className="text-sm font-semibold uppercase tracking-[0.12em] text-[#7c4d2c]">
              Organizations
            </p>
            <h2 className="mt-3 text-xl font-bold">Browse organizations</h2>
            <p className="mt-2 text-sm leading-6 text-[#63717a]">
              Open an organization workspace to manage its users and guides.
            </p>
          </Link>

          <Link
            href="/platform-admin/templates"
            className="rounded-lg border border-[#d6cab8] bg-white p-6 transition hover:border-[#1e3a3a]"
          >
            <p className="text-sm font-semibold uppercase tracking-[0.12em] text-[#7c4d2c]">
              Communication
            </p>
            <h2 className="mt-3 text-xl font-bold">Manage templates</h2>
            <p className="mt-2 text-sm leading-6 text-[#63717a]">
              Maintain the reusable messages used when accounts are created.
            </p>
          </Link>
        </div>
      </div>
    </main>
  );
}