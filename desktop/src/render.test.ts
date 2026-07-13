import { describe, expect, it, vi } from "vitest";
import { renderApp } from "./render";
import type { BridgeClient, Snapshot, SyncProposal } from "./types";

const snapshot: Snapshot = {
  config: {
    rootDir: "/tmp/config",
    activeId: 0,
    activeConfigDir: "/tmp/config/user_config_0",
    tasksPath: "/tmp/config/tasks/tasks.json",
    deadlinesPath: "/tmp/config/user_config_0/ddl.json",
    habitsPath: "/tmp/config/user_config_0/habits.toml",
    recordsPath: "/tmp/config/tasks/record.json"
  },
  today: {
    date: "2026-04-28",
    weekday: "tuesday",
    parity: "even"
  },
  schedule: {
    isSkipped: false,
    current: "pomodoro: Draft proposal at 09:00",
    next: "short_break at 09:25",
    timeToNext: "7m",
    events: [
      {
        time: "09:00",
        label: "pomodoro: Draft proposal",
        block: "pomodoro",
        syncable: false
      },
      {
        time: "09:25",
        label: "short_break",
        block: "short_break",
        syncable: false
      }
    ],
    hasSyncedOverlay: true
  },
  tasks: [
    {
      description: "Draft proposal",
      priority: 9,
      type: "1",
      typeName: "read papers",
      alarmFrom: null,
      procrastinated: false,
      procrastinateDays: null
    }
  ],
  deadlines: [
    { event: "Submit paper", deadline: "2026-05-10", daysLeft: 12, status: "ok" }
  ],
  habits: [
    { id: "1", description: "Read", completed: false },
    { id: "2", description: "Stretch", completed: true }
  ],
  taskTypes: {
    "1": "read papers",
    "2": "gym work",
    "3": "coding",
    "4": "other"
  },
  history: [
    {
      description: "Old task",
      priority: 5,
      startedAt: "2026-04-27T09:00:00",
      endedAt: "2026-04-27T11:30:00",
      duration: "2h 30m"
    }
  ]
};

const syncProposal: SyncProposal = {
  summary: "Matched priority work to the open focus blocks.",
  plan: {
    target_date: "2026-04-28",
    parity: "even",
    weekday: "tuesday",
    assignments: {
      "09:00": { block: "pomodoro", title: "Draft proposal" }
    }
  },
  preview: [
    {
      time: "09:00",
      label: "pomodoro: Draft proposal",
      block: "pomodoro"
    }
  ]
};

async function flushAsync(): Promise<void> {
  await Promise.resolve();
  await Promise.resolve();
}

describe("renderApp", () => {
  it("renders the daily command center", async () => {
    const root = document.createElement("main");
    const client: BridgeClient = {
      send: vi.fn().mockResolvedValue(snapshot)
    };

    await renderApp(root, client);

    expect(root.textContent).toContain("Daily Command Center");
    expect(root.textContent).toContain("pomodoro: Draft proposal");
    expect(root.textContent).toContain("Draft proposal");
    expect(root.textContent).toContain("Submit paper");
    expect(root.textContent).toContain("Read");
    expect(root.textContent).toContain("Stretch");
    expect(root.textContent).toContain("read papers");
    expect(root.textContent).toContain("Old task");
    expect(root.textContent).toContain("2h 30m");
    expect(root.querySelector(".grid")).not.toBeNull();
    expect(root.querySelector(".now-panel")).not.toBeNull();
    expect(root.querySelector(".timeline-panel")).not.toBeNull();
    expect(root.querySelector(".queue-panel")).not.toBeNull();
    expect(root.querySelector(".quick-panel")).not.toBeNull();
    expect(root.querySelector(".history-panel")).not.toBeNull();
    expect(root.querySelector(".type-badge")).not.toBeNull();
  });

  it("assigns different colors to different task types without duplication", async () => {
    const root = document.createElement("main");
    const customSnapshot: Snapshot = {
      ...snapshot,
      taskTypes: {
        "1": "type1",
        "2": "type2",
        "3": "type3",
        "4": "type4",
        "5": "type5",
      },
      tasks: [
        { description: "Task 1", priority: 1, type: "1", typeName: "type1", alarmFrom: null, procrastinated: false, procrastinateDays: null },
        { description: "Task 2", priority: 2, type: "2", typeName: "type2", alarmFrom: null, procrastinated: false, procrastinateDays: null },
        { description: "Task 3", priority: 3, type: "3", typeName: "type3", alarmFrom: null, procrastinated: false, procrastinateDays: null },
        { description: "Task 4", priority: 4, type: "4", typeName: "type4", alarmFrom: null, procrastinated: false, procrastinateDays: null },
        { description: "Task 5", priority: 5, type: "5", typeName: "type5", alarmFrom: null, procrastinated: false, procrastinateDays: null },
      ]
    };
    const client: BridgeClient = {
      send: vi.fn().mockResolvedValue(customSnapshot)
    };

    await renderApp(root, client);

    const badges = root.querySelectorAll(".type-badge");
    expect(badges.length).toBe(5);

    const colors = Array.from(badges).map(badge => {
      const style = badge.getAttribute("style") || "";
      const match = style.match(/background:\s*([^;]+)/);
      return match ? match[1].trim() : "";
    });

    colors.forEach(c => expect(c).not.toBe(""));
    const uniqueColors = new Set(colors);
    expect(uniqueColors.size).toBe(5);
  });

  it("sends task add command and refreshes", async () => {
    const root = document.createElement("main");
    const client: BridgeClient = {
      send: vi.fn().mockResolvedValue(snapshot)
    };

    await renderApp(root, client);

    const input = root.querySelector<HTMLInputElement>(
      "[data-testid='task-description']"
    );
    const priority = root.querySelector<HTMLInputElement>(
      "[data-testid='task-priority']"
    );
    const button = root.querySelector<HTMLButtonElement>("[data-testid='task-add']");
    expect(input).not.toBeNull();
    expect(priority).not.toBeNull();
    expect(button).not.toBeNull();

    input!.value = "Review PR";
    priority!.value = "8";
    button!.click();
    await flushAsync();

    expect(client.send).toHaveBeenCalledWith("task_add", {
      description: "Review PR",
      type: "1",
      priority: 8
    });
  });

  it("sends task deletion command", async () => {
    const root = document.createElement("main");
    const client: BridgeClient = {
      send: vi.fn().mockResolvedValue(snapshot)
    };

    await renderApp(root, client);

    const button = root.querySelector<HTMLButtonElement>(
      "[data-testid='task-delete']"
    );
    expect(button).not.toBeNull();

    button!.click();
    await flushAsync();

    expect(client.send).toHaveBeenCalledWith("task_delete", {
      description: "Draft proposal"
    });
  });

  it("sends habit completion set from checked rows", async () => {
    const root = document.createElement("main");
    const client: BridgeClient = {
      send: vi.fn().mockResolvedValue(snapshot)
    };

    await renderApp(root, client);

    const firstHabit = root.querySelector<HTMLInputElement>(
      "[data-habit-id='1']"
    );
    expect(firstHabit).not.toBeNull();

    firstHabit!.checked = true;
    firstHabit!.dispatchEvent(new Event("change"));
    await flushAsync();

    expect(client.send).toHaveBeenCalledWith("habit_mark", {
      habitIds: ["1", "2"]
    });
  });

  it("sends deadline add command", async () => {
    const root = document.createElement("main");
    const client: BridgeClient = {
      send: vi.fn().mockResolvedValue(snapshot)
    };

    await renderApp(root, client);

    const event = root.querySelector<HTMLInputElement>(
      "[data-testid='deadline-event']"
    );
    const date = root.querySelector<HTMLInputElement>(
      "[data-testid='deadline-date']"
    );
    const button = root.querySelector<HTMLButtonElement>(
      "[data-testid='deadline-add']"
    );
    expect(event).not.toBeNull();
    expect(date).not.toBeNull();
    expect(button).not.toBeNull();

    event!.value = "File taxes";
    date!.value = "2026-05-01";
    button!.click();
    await flushAsync();

    expect(client.send).toHaveBeenCalledWith("deadline_add", {
      event: "File taxes",
      date: "2026-05-01"
    });
  });

  it("sends deadline deletion command", async () => {
    const root = document.createElement("main");
    const client: BridgeClient = {
      send: vi.fn().mockResolvedValue(snapshot)
    };

    await renderApp(root, client);

    const button = root.querySelector<HTMLButtonElement>(
      "[data-testid='deadline-delete']"
    );
    expect(button).not.toBeNull();

    button!.click();
    await flushAsync();

    expect(client.send).toHaveBeenCalledWith("deadline_delete", {
      event: "Submit paper"
    });
  });

  it("generates and accepts a sync proposal", async () => {
    const root = document.createElement("main");
    const send = vi.fn(async (command: string) => {
      if (command === "sync_generate") {
        return syncProposal;
      }
      return snapshot;
    }) as unknown as BridgeClient["send"];
    const client: BridgeClient = {
      send
    };

    await renderApp(root, client);

    const feedback = root.querySelector<HTMLTextAreaElement>(
      "[data-testid='sync-feedback']"
    );
    const generate = root.querySelector<HTMLButtonElement>(
      "[data-testid='sync-generate']"
    );
    expect(feedback).not.toBeNull();
    expect(generate).not.toBeNull();

    feedback!.value = "Keep writing earlier.";
    generate!.click();
    await flushAsync();

    expect(client.send).toHaveBeenCalledWith("sync_generate", {
      feedback: ["Keep writing earlier."]
    });
    expect(root.textContent).toContain("Matched priority work");

    const accept = root.querySelector<HTMLButtonElement>(
      "[data-testid='sync-accept']"
    );
    expect(accept).not.toBeNull();
    accept!.click();
    await flushAsync();

    expect(client.send).toHaveBeenCalledWith("sync_accept", {
      plan: syncProposal.plan
    });
  });
});
