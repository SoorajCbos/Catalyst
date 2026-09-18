"use client";

import { FormEvent, useState } from "react";

type ChatMessage = {
  sender: "user" | "agent";
  text: string;
};

type AgentResponse = {
  reply: string;
  agentName: string;
  contextLoaded: boolean;
};

export default function AgentPage() {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const prompt = message.trim();

    if (!prompt) {
      return;
    }

    setError("");
    setMessage("");
    setIsSending(true);

    setMessages((current) => [
      ...current,
      { sender: "user", text: prompt },
    ]);

    try {
      const response = await fetch("/api/v1/agents/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: prompt }),
      });

      const data = (await response.json()) as AgentResponse & {
        detail?: string;
      };

      if (!response.ok) {
        throw new Error(data.detail ?? "Agent request failed.");
      }

      setMessages((current) => [
        ...current,
        { sender: "agent", text: data.reply },
      ]);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Agent request failed."
      );
    } finally {
      setIsSending(false);
    }
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <h1 className="text-2xl font-bold">Agent Console</h1>

      <p className="mt-2 text-sm text-[#63717a]">
        Ask the agent questions using your approved organization guides.
      </p>

      <section className="mt-8 rounded-lg border border-[#d6cab8] bg-white p-6">
        <div className="min-h-80 space-y-4">
          {messages.length === 0 ? (
            <p className="text-sm text-[#63717a]">
              No messages yet.
            </p>
          ) : (
            messages.map((item, index) => (
              <div
                key={`${item.sender}-${index}`}
                className={
                  item.sender === "user"
                    ? "ml-auto max-w-[80%] rounded-lg bg-[#1e3a3a] p-3 text-sm text-white"
                    : "mr-auto max-w-[80%] rounded-lg bg-[#f3f0e8] p-3 text-sm"
                }
              >
                {item.text}
              </div>
            ))
          )}
        </div>

        {error ? (
          <p className="mt-4 text-sm text-red-700">{error}</p>
        ) : null}

        <form onSubmit={handleSubmit} className="mt-6 flex gap-3">
          <input
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            maxLength={4000}
            placeholder="Ask the agent..."
            className="h-11 flex-1 rounded-md border border-[#cfc4b3] px-3 text-sm"
          />

          <button
            type="submit"
            disabled={isSending}
            className="rounded-md bg-[#1e3a3a] px-5 text-sm font-semibold text-white disabled:opacity-50"
          >
            {isSending ? "Sending..." : "Send"}
          </button>
        </form>
      </section>
    </main>
  );
}