"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

type Agent = {
  key: string;
  name: string;
  description: string;
  available: boolean;
  acceptsImages: boolean;
};

type ChatSession = {
  sessionId: string;
  agentKey: string;
  title: string;
  lastMessageAt: string;
};

type ChatMessage = {
  messageId: string;
  sender: string;
  content: string;
};

type AgentChatResponse = {
  reply: string;
  agentName: string;
  contextLoaded: boolean;
  callId: string;
  tokensUsed: number;
  sessionId: string;
};

export default function AgentWorkspacePage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState("");
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [message, setMessage] = useState("");
  const [isLoadingAgents, setIsLoadingAgents] = useState(true);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState("");

  const loadSessions = useCallback(async () => {
    try {
      const response = await fetch("/api/v1/agents/sessions");

      if (response.ok) {
        setSessions((await response.json()) as ChatSession[]);
      }
    } catch {
      // The list refreshes again after the next message.
    }
  }, []);

  useEffect(() => {
    async function loadAgents() {
      try {
        const response = await fetch("/api/v1/agents");

        if (!response.ok) {
          throw new Error("Could not load agents.");
        }

        const data = (await response.json()) as Agent[];
        setAgents(data);

        const initialAgent = data.find((agent) => agent.available) ?? data[0];

        if (initialAgent) {
          setSelectedAgent(initialAgent.key);
        }
      } catch (loadError) {
        setError(
          loadError instanceof Error
            ? loadError.message
            : "Could not load agents."
        );
      } finally {
        setIsLoadingAgents(false);
      }
    }

    void loadAgents();
    void loadSessions();
  }, [loadSessions]);

  function startNewChat() {
    if (isSending) {
      return;
    }

    setActiveSessionId(null);
    setMessages([]);
    setError("");
  }

  async function openSession(session: ChatSession) {
    if (isSending) {
      return;
    }

    setError("");
    setActiveSessionId(session.sessionId);
    setSelectedAgent(session.agentKey);
    setIsLoadingMessages(true);

    try {
      const response = await fetch(
        `/api/v1/agents/sessions/${encodeURIComponent(
          session.sessionId
        )}/messages`
      );

      if (!response.ok) {
        throw new Error("Could not load this chat.");
      }

      setMessages((await response.json()) as ChatMessage[]);
    } catch (loadError) {
      setMessages([]);
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Could not load this chat."
      );
    } finally {
      setIsLoadingMessages(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const prompt = message.trim();

    if (!prompt || !selectedAgent || isSending) {
      return;
    }

    setError("");
    setMessage("");
    setIsSending(true);
    setMessages((current) => [
      ...current,
      { messageId: crypto.randomUUID(), sender: "user", content: prompt },
    ]);

    try {
      const response = await fetch("/api/v1/agents/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: prompt,
          agentKey: selectedAgent,
          images: [],
          sessionId: activeSessionId,
        }),
      });

      const data = (await response.json()) as AgentChatResponse & {
        detail?: unknown;
      };

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Agent request failed."
        );
      }

      setActiveSessionId(data.sessionId);
      setMessages((current) => [
        ...current,
        {
          messageId: crypto.randomUUID(),
          sender: "agent",
          content: data.reply,
        },
      ]);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Agent request failed."
      );
    } finally {
      setIsSending(false);
      void loadSessions();
    }
  }

  return (
    <main className="h-[calc(100vh-73px)] overflow-hidden bg-[#f3f0e8] text-[#172026]">
      <div className="grid h-full grid-cols-[250px_minmax(0,1fr)_280px]">
        <aside className="overflow-y-auto border-r border-[#d6cab8] bg-[#20252b] p-4 text-white">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold uppercase tracking-wide">
              Chats
            </h2>

            <button
              type="button"
              onClick={startNewChat}
              disabled={isSending}
              className="rounded border border-zinc-600 px-2 py-1 text-xs hover:bg-[#292f36] disabled:opacity-50"
            >
              + New
            </button>
          </div>

          <div className="mt-4 space-y-2">
            {isSending && activeSessionId === null ? (
              <div className="rounded border border-[#4b8f8f] bg-[#292f36] p-3">
                <p className="truncate text-xs">New chat</p>
                <p className="mt-1 text-[11px] text-amber-300">running</p>
              </div>
            ) : null}

            {sessions.length === 0 && !isSending ? (
              <p className="text-xs text-zinc-400">No chats yet.</p>
            ) : (
              sessions.map((session) => {
                const isActive = activeSessionId === session.sessionId;

                return (
                  <button
                    key={session.sessionId}
                    type="button"
                    onClick={() => void openSession(session)}
                    className={`w-full rounded border p-3 text-left ${
                      isActive
                        ? "border-[#4b8f8f] bg-[#2f3a40]"
                        : "border-zinc-700 bg-[#292f36] hover:bg-[#2f353c]"
                    }`}
                  >
                    <p className="truncate text-xs leading-5">
                      {session.title}
                    </p>
                    <p className="mt-1 text-[11px] text-zinc-400">
                      {isActive && isSending ? (
                        <span className="text-amber-300">running</span>
                      ) : (
                        session.lastMessageAt
                      )}
                    </p>
                  </button>
                );
              })
            )}
          </div>
        </aside>

        <section className="flex min-w-0 flex-col bg-white">
          <header className="border-b border-[#d6cab8] px-6 py-4">
            <h1 className="text-lg font-bold">Agent Workspace</h1>
            <p className="text-xs text-[#63717a]">
              Chat with an approved agent. Chats are saved and can be reopened
              from the left panel.
            </p>
          </header>

          <div className="flex-1 space-y-4 overflow-y-auto p-6">
            {isLoadingMessages ? (
              <p className="text-sm text-[#63717a]">Loading chat...</p>
            ) : messages.length === 0 ? (
              <div className="flex h-full items-center justify-center">
                <p className="text-sm text-[#63717a]">
                  Select an agent and start a conversation.
                </p>
              </div>
            ) : (
              messages.map((item) => (
                <div
                  key={item.messageId}
                  className={
                    item.sender === "user"
                      ? "ml-auto max-w-[75%] whitespace-pre-wrap rounded-lg bg-[#1e3a3a] p-3 text-sm text-white"
                      : "mr-auto max-w-[75%] whitespace-pre-wrap rounded-lg bg-[#f3f0e8] p-3 text-sm"
                  }
                >
                  {item.content}
                </div>
              ))
            )}
          </div>

          <div className="border-t border-[#d6cab8] p-4">
            {error ? (
              <p className="mb-3 text-sm text-red-700">{error}</p>
            ) : null}

            <form onSubmit={handleSubmit} className="flex gap-3">
              <textarea
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                maxLength={500}
                rows={2}
                placeholder="Ask the selected agent..."
                className="min-h-12 flex-1 resize-none rounded-md border border-[#cfc4b3] px-3 py-2 text-sm"
              />

              <button
                type="submit"
                disabled={isSending || !selectedAgent}
                className="rounded-md bg-[#1e3a3a] px-5 text-sm font-semibold text-white disabled:opacity-50"
              >
                {isSending ? "Running..." : "Send"}
              </button>
            </form>
          </div>
        </section>

        <aside className="overflow-y-auto border-l border-[#d6cab8] bg-[#fffdf8] p-4">
          <h2 className="text-sm font-bold uppercase tracking-wide">Agents</h2>

          <div className="mt-4 space-y-3">
            {isLoadingAgents ? (
              <p className="text-xs text-[#63717a]">Loading agents...</p>
            ) : (
              agents.map((agent) => (
                <button
                  key={agent.key}
                  type="button"
                  onClick={() => setSelectedAgent(agent.key)}
                  className={`w-full rounded-md border p-3 text-left ${
                    selectedAgent === agent.key
                      ? "border-[#1e3a3a] bg-[#e8f0ed]"
                      : "border-[#d6cab8] bg-white"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-semibold">{agent.name}</p>
                    <span
                      className={`h-2.5 w-2.5 rounded-full ${
                        agent.available ? "bg-emerald-600" : "bg-zinc-400"
                      }`}
                    />
                  </div>

                  <p className="mt-2 text-xs leading-5 text-[#63717a]">
                    {agent.description}
                  </p>

                  <p className="mt-2 text-[11px] font-semibold">
                    {agent.available ? "Available" : "Not configured"}
                  </p>
                </button>
              ))
            )}
          </div>
        </aside>
      </div>
    </main>
  );
}