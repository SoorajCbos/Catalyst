"use client";

import {
  FormEvent,
  useEffect,
  useState,
} from "react";

type Agent = {
  key: string;
  name: string;
  description: string;
  agentId: string;
  available: boolean;
};

type ChatMessage = {
  id: string;
  sender: "user" | "agent";
  text: string;
};

type TaskStatus = "running" | "completed" | "failed";

type AgentTask = {
  id: string;
  title: string;
  status: TaskStatus;
};

type AgentChatResponse = {
  reply: string;
  agentName: string;
  contextLoaded: boolean;
  callId: string;
};

export default function AgentWorkspacePage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [message, setMessage] = useState("");
  const [isLoadingAgents, setIsLoadingAgents] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadAgents() {
      try {
        const response = await fetch("/api/v1/agents");

        if (!response.ok) {
          throw new Error("Could not load agents.");
        }

        const data = (await response.json()) as Agent[];

        setAgents(data);

        const initialAgent =
          data.find((agent) => agent.available) ?? data[0];

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
  }, []);

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    const prompt = message.trim();

    if (!prompt || !selectedAgent) {
      return;
    }

    const taskId = crypto.randomUUID();

    setError("");
    setMessage("");
    setIsSending(true);

    setMessages((current) => [
      ...current,
      {
        id: crypto.randomUUID(),
        sender: "user",
        text: prompt,
      },
    ]);

    setTasks((current) => [
      {
        id: taskId,
        title:
          prompt.length > 45
            ? `${prompt.slice(0, 45)}...`
            : prompt,
        status: "running",
      },
      ...current,
    ]);

    try {
      const response = await fetch("/api/v1/agents/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: prompt,
          agentKey: selectedAgent,
        }),
      });

      const data = (await response.json()) as
        AgentChatResponse & {
          detail?: string;
        };

      if (!response.ok) {
        throw new Error(data.detail ?? "Agent request failed.");
      }

      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          sender: "agent",
          text: data.reply,
        },
      ]);

      setTasks((current) =>
        current.map((task) =>
          task.id === taskId
            ? { ...task, status: "completed" }
            : task
        )
      );
    } catch (requestError) {
      setTasks((current) =>
        current.map((task) =>
          task.id === taskId
            ? { ...task, status: "failed" }
            : task
        )
      );

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
    <main className="h-[calc(100vh-73px)] overflow-hidden bg-[#f3f0e8] text-[#172026]">
      <div className="grid h-full grid-cols-[250px_minmax(0,1fr)_280px]">
        <aside className="overflow-y-auto border-r border-[#d6cab8] bg-[#20252b] p-4 text-white">
          <h2 className="text-sm font-bold uppercase tracking-wide">
            Tasks
          </h2>

          <div className="mt-4 space-y-2">
            {tasks.length === 0 ? (
              <p className="text-xs text-zinc-400">
                No tasks started.
              </p>
            ) : (
              tasks.map((task) => (
                <div
                  key={task.id}
                  className="rounded border border-zinc-700 bg-[#292f36] p-3"
                >
                  <p className="text-xs leading-5">
                    {task.title}
                  </p>

                  <p
                    className={`mt-2 text-[11px] font-semibold ${
                      task.status === "completed"
                        ? "text-emerald-400"
                        : task.status === "failed"
                          ? "text-red-400"
                          : "text-amber-300"
                    }`}
                  >
                    {task.status}
                  </p>
                </div>
              ))
            )}
          </div>
        </aside>

        <section className="flex min-w-0 flex-col bg-white">
          <header className="border-b border-[#d6cab8] px-6 py-4">
            <h1 className="text-lg font-bold">
              Agent Workspace
            </h1>

            <p className="text-xs text-[#63717a]">
              Chat with an approved agent and monitor its tasks.
            </p>
          </header>

          <div className="flex-1 space-y-4 overflow-y-auto p-6">
            {messages.length === 0 ? (
              <div className="flex h-full items-center justify-center">
                <p className="text-sm text-[#63717a]">
                  Select an agent and start a conversation.
                </p>
              </div>
            ) : (
              messages.map((item) => (
                <div
                  key={item.id}
                  className={
                    item.sender === "user"
                      ? "ml-auto max-w-[75%] rounded-lg bg-[#1e3a3a] p-3 text-sm text-white"
                      : "mr-auto max-w-[75%] rounded-lg bg-[#f3f0e8] p-3 text-sm"
                  }
                >
                  {item.text}
                </div>
              ))
            )}
          </div>

          <div className="border-t border-[#d6cab8] p-4">
            {error ? (
              <p className="mb-3 text-sm text-red-700">
                {error}
              </p>
            ) : null}

            <form
              onSubmit={handleSubmit}
              className="flex gap-3"
            >
              <textarea
                value={message}
                onChange={(event) =>
                  setMessage(event.target.value)
                }
                maxLength={4000}
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
          <h2 className="text-sm font-bold uppercase tracking-wide">
            Agents
          </h2>

          <div className="mt-4 space-y-3">
            {isLoadingAgents ? (
              <p className="text-xs text-[#63717a]">
                Loading agents...
              </p>
            ) : (
              agents.map((agent) => (
                <button
                  key={agent.key}
                  type="button"
                  onClick={() =>
                    setSelectedAgent(agent.key)
                  }
                  className={`w-full rounded-md border p-3 text-left ${
                    selectedAgent === agent.key
                      ? "border-[#1e3a3a] bg-[#e8f0ed]"
                      : "border-[#d6cab8] bg-white"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-semibold">
                      {agent.name}
                    </p>

                    <span
                      className={`h-2.5 w-2.5 rounded-full ${
                        agent.available
                          ? "bg-emerald-600"
                          : "bg-zinc-400"
                      }`}
                    />
                  </div>

                  <p className="mt-2 text-xs leading-5 text-[#63717a]">
                    {agent.description}
                  </p>

                  <p className="mt-2 text-[11px] font-semibold">
                    {agent.available
                      ? "Available"
                      : "Not configured"}
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