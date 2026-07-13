import {
  CalendarPlus,
  Check,
  History,
  Plus,
  RefreshCw,
  Trash2,
  WandSparkles,
} from "lucide";
import type { BridgeClient, Snapshot, SyncProposal } from "./types";

type SvgAttrs = Record<string, string | number>;
type SvgNode = readonly [tag: string, attrs: SvgAttrs, children?: readonly SvgNode[]];

function getTaskTypeStyle(typeId: string, taskTypes: Record<string, string>): string {
  if (!taskTypes) return "";
  const sortedKeys = Object.keys(taskTypes).sort((a, b) => {
    const na = Number.parseInt(a, 10);
    const nb = Number.parseInt(b, 10);
    if (!Number.isNaN(na) && !Number.isNaN(nb)) return na - nb;
    return a.localeCompare(b);
  });
  const index = sortedKeys.indexOf(typeId);
  if (index === -1) return "";

  const total = sortedKeys.length;
  const hue = total > 0 ? (index * (360 / total)) % 360 : 0;

  return `style="background: hsl(${hue}, 65%, 92%); color: hsl(${hue}, 75%, 32%); border: 1px solid hsl(${hue}, 75%, 85%);"`;
}

const refreshIcon = renderIcon(RefreshCw, { width: 16, height: 16 });
const plusIcon = renderIcon(Plus, { width: 16, height: 16 });
const trashIcon = renderIcon(Trash2, { width: 16, height: 16 });
const calendarIcon = renderIcon(CalendarPlus, { width: 16, height: 16 });
const checkIcon = renderIcon(Check, { width: 16, height: 16 });
const sparkIcon = renderIcon(WandSparkles, { width: 16, height: 16 });
const historyIcon = renderIcon(History, { width: 16, height: 16 });

type AppState = {
  syncProposal: SyncProposal | null;
  syncFeedback: string[];
  typeEditorOpen: boolean;
};

export async function renderApp(
  root: HTMLElement,
  client: BridgeClient
): Promise<void> {
  const state: AppState = {
    syncProposal: null,
    syncFeedback: [],
    typeEditorOpen: false,
  };
  root.innerHTML = `<section class="shell"><p class="muted">Loading...</p></section>`;

  async function load(): Promise<void> {
    try {
      const snapshot = await client.send<Snapshot>("status_snapshot", {});
      renderSnapshot(root, client, snapshot, load, state);
    } catch (error) {
      renderError(root, error);
    }
  }

  await load();
}

function renderError(root: HTMLElement, error: unknown): void {
  const message = error instanceof Error ? error.message : String(error);
  root.innerHTML = `
    <section class="shell">
      <div class="panel error-panel">
        <p class="eyebrow">Desktop Bridge</p>
        <h1>Could not load schedule</h1>
        <p>${escapeHtml(message)}</p>
      </div>
    </section>
  `;
}

function renderSnapshot(
  root: HTMLElement,
  client: BridgeClient,
  snapshot: Snapshot,
  reload: () => Promise<void>,
  state: AppState
): void {
  root.innerHTML = `
    <section class="shell">
      <header class="topbar">
        <div>
          <p class="eyebrow">Schedule Everything</p>
          <h1>Daily Command Center</h1>
          <p class="muted">${snapshot.today.date} · ${snapshot.today.weekday} · ${snapshot.today.parity} week · config ${snapshot.config.activeId}</p>
        </div>
        <button class="icon-button" type="button" data-testid="refresh" aria-label="Refresh">${refreshIcon}</button>
      </header>
      <section class="grid">
        ${renderNowNext(snapshot)}
        ${renderTimeline(snapshot)}
        ${renderQueue(snapshot)}
        ${renderQuickAdd(snapshot, state)}
        ${renderHistory(snapshot)}
      </section>
    </section>
  `;

  root
    .querySelector<HTMLButtonElement>("[data-testid='refresh']")
    ?.addEventListener("click", () => {
      runAction(root, reload);
    });

  root
    .querySelector<HTMLButtonElement>("[data-testid='task-add']")
    ?.addEventListener("click", () => {
      runAction(root, () => addTask(root, client, reload));
    });

  root
    .querySelectorAll<HTMLButtonElement>("[data-testid='task-delete']")
    .forEach((button) => {
      button.addEventListener("click", () => {
        runAction(root, () => deleteTask(button, client, reload));
      });
    });

  root
    .querySelector<HTMLButtonElement>("[data-testid='deadline-add']")
    ?.addEventListener("click", () => {
      runAction(root, () => addDeadline(root, client, reload));
    });

  root
    .querySelectorAll<HTMLButtonElement>("[data-testid='deadline-delete']")
    .forEach((button) => {
      button.addEventListener("click", () => {
        runAction(root, () => deleteDeadline(button, client, reload));
      });
    });

  root
    .querySelectorAll<HTMLInputElement>("[data-testid='habit-check']")
    .forEach((checkbox) => {
      checkbox.addEventListener("change", () => {
        runAction(root, () => markHabits(root, client, reload));
      });
    });

  root
    .querySelector<HTMLButtonElement>("[data-testid='sync-generate']")
    ?.addEventListener("click", () => {
      runAction(root, () => generateSync(root, client, snapshot, reload, state));
    });

  root
    .querySelector<HTMLButtonElement>("[data-testid='sync-accept']")
    ?.addEventListener("click", () => {
      runAction(root, () => acceptSync(client, reload, state));
    });

  root
    .querySelector<HTMLButtonElement>("[data-testid='type-editor-toggle']")
    ?.addEventListener("click", () => {
      state.typeEditorOpen = !state.typeEditorOpen;
      renderSnapshot(root, client, snapshot, reload, state);
    });

  root
    .querySelector<HTMLButtonElement>("[data-testid='type-editor-save']")
    ?.addEventListener("click", () => {
      runAction(root, () => saveTaskTypes(root, client, reload));
    });
}

function renderNowNext(snapshot: Snapshot): string {
  const current = snapshot.schedule.current ?? "Idle";
  const next = snapshot.schedule.next ?? "No upcoming events";
  const timeToNext = snapshot.schedule.timeToNext
    ? `in ${snapshot.schedule.timeToNext}`
    : "";
  return `
    <article class="panel now-panel">
      <p class="eyebrow">Now</p>
      <h2>${escapeHtml(current)}</h2>
      <div class="next-line">
        <span>Next</span>
        <strong>${escapeHtml(next)}</strong>
        <em>${escapeHtml(timeToNext)}</em>
      </div>
      <span class="sync-pill">${snapshot.schedule.hasSyncedOverlay ? "Synced" : "Base schedule"}</span>
    </article>
  `;
}

function renderTimeline(snapshot: Snapshot): string {
  const rows = snapshot.schedule.events
    .map(
      (event) => `
        <li class="timeline-row">
          <time>${escapeHtml(event.time)}</time>
          <span class="block-dot ${cssClass(event.block)}"></span>
          <span>${escapeHtml(event.label)}</span>
        </li>
      `
    )
    .join("");

  return `
    <article class="panel timeline-panel">
      <div class="panel-heading">
        <p class="eyebrow">Today Timeline</p>
      </div>
      <ol class="timeline">${rows}</ol>
    </article>
  `;
}

function renderQueue(snapshot: Snapshot): string {
  const tasks = snapshot.tasks
    .slice(0, 8)
    .map((task) => {
      const rowClass = task.alarmFrom
        ? "queue-row postponed"
        : task.procrastinated
          ? "queue-row procrastinated"
          : "queue-row";

      let label = escapeHtml(task.description);
      if (task.alarmFrom) {
        const today = new Date(snapshot.today.date);
        const alarmDate = new Date(task.alarmFrom);
        const daysLeft = Math.round(
          (alarmDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24)
        );
        const suffix = daysLeft <= 1 ? " (coming tomorrow)" : ` (coming in ${daysLeft} days)`;
        label = `\u{1F4A4} ${label}${escapeHtml(suffix)}`;
      } else if (task.procrastinated) {
        const age = task.procrastinateDays;
        const suffix = age === null ? "" : age === 0 ? " (deferred today)" : age === 1 ? " (1 day overdue)" : ` (${age} days overdue)`;
        label = `\u23F3 ${label}${escapeHtml(suffix)}`;
      }

      const badgeStyle = getTaskTypeStyle(task.type, snapshot.taskTypes || {});
      const typeBadge = task.typeName
        ? `<span class="type-badge" ${badgeStyle}>${escapeHtml(task.typeName)}</span>`
        : "";

      return `
        <li class="${rowClass}">
          <span>${label}</span>
          ${typeBadge}
          <strong>${task.priority}</strong>
          <button class="icon-button subtle" type="button" data-testid="task-delete" data-description="${escapeHtml(task.description)}" aria-label="Delete task ${escapeHtml(task.description)}" title="Delete task">${trashIcon}</button>
        </li>
      `;
    })
    .join("");
  const deadlines = snapshot.deadlines
    .slice(0, 4)
    .map(
      (deadline) => `
        <li class="queue-row deadline ${cssClass(deadline.status)}">
          <span>${escapeHtml(deadline.event)}</span>
          <strong>${deadline.daysLeft === null ? "Invalid" : `${deadline.daysLeft}d`}</strong>
          <button class="icon-button subtle" type="button" data-testid="deadline-delete" data-event="${escapeHtml(deadline.event)}" aria-label="Delete deadline ${escapeHtml(deadline.event)}" title="Delete deadline">${trashIcon}</button>
        </li>
      `
    )
    .join("");
  const habits = snapshot.habits
    .map(
      (habit) => `
        <label class="habit-row">
          <input data-testid="habit-check" data-habit-id="${escapeHtml(habit.id)}" type="checkbox" ${habit.completed ? "checked" : ""} />
          <span>${escapeHtml(habit.description)}</span>
        </label>
      `
    )
    .join("");

  return `
    <article class="panel queue-panel">
      <p class="eyebrow">Work Queue</p>
      <h3>Tasks</h3>
      <ul class="queue-list">${tasks}</ul>
      <h3>Deadlines</h3>
      <ul class="queue-list">${deadlines}</ul>
      <h3>Habits</h3>
      <div class="habit-list">${habits}</div>
    </article>
  `;
}

function renderQuickAdd(snapshot: Snapshot, state: AppState): string {
  const typeOptions = Object.entries(snapshot.taskTypes)
    .sort(([a], [b]) => {
      const na = Number.parseInt(a, 10);
      const nb = Number.parseInt(b, 10);
      if (!Number.isNaN(na) && !Number.isNaN(nb)) return na - nb;
      return a.localeCompare(b);
    })
    .map(([id, name]) => `<option value="${escapeHtml(id)}">${escapeHtml(name)}</option>`)
    .join("");

  const typeEditor = state.typeEditorOpen
    ? `
      <div class="type-editor" data-testid="type-editor">
        ${Object.entries(snapshot.taskTypes)
          .sort(([a], [b]) => {
            const na = Number.parseInt(a, 10);
            const nb = Number.parseInt(b, 10);
            if (!Number.isNaN(na) && !Number.isNaN(nb)) return na - nb;
            return a.localeCompare(b);
          })
          .map(([id, name]) => {
            const badgeStyle = getTaskTypeStyle(id, snapshot.taskTypes || {});
            return `
              <div class="type-row">
                <span class="type-color-dot" ${badgeStyle}></span>
                <input data-testid="type-key" type="text" value="${escapeHtml(id)}" readonly />
                <input data-testid="type-name" type="text" value="${escapeHtml(name)}" data-type-key="${escapeHtml(id)}" />
              </div>
            `;
          })
          .join("")}
        <button data-testid="type-editor-save" class="secondary-button" type="button">Save Types</button>
      </div>
    `
    : "";

  return `
    <article class="panel quick-panel">
      <p class="eyebrow">Quick Add</p>
      <div class="form-row">
        <input data-testid="task-description" type="text" autocomplete="off" placeholder="New task" />
        <select data-testid="task-type" aria-label="Task type">${typeOptions}</select>
        <input data-testid="task-priority" type="number" min="1" max="10" value="5" aria-label="Task priority" />
        <button data-testid="task-add" class="primary-button" type="button">${plusIcon}<span>Add</span></button>
      </div>
      <div class="deadline-form">
        <input data-testid="deadline-event" type="text" autocomplete="off" placeholder="Deadline" />
        <input data-testid="deadline-date" type="text" autocomplete="off" placeholder="YYYY-MM-DD" />
        <button data-testid="deadline-add" class="secondary-button" type="button">${calendarIcon}<span>Add</span></button>
      </div>
      <div class="sync-box">
        <textarea data-testid="sync-feedback" rows="3" placeholder="Sync adjustment"></textarea>
        <div class="sync-actions">
          <button data-testid="sync-generate" class="primary-button sync-button" type="button">${sparkIcon}<span>${state.syncProposal ? "Regenerate" : "Sync Today"}</span></button>
          ${
            state.syncProposal
              ? `<button data-testid="sync-accept" class="primary-button accept-button" type="button">${checkIcon}<span>Accept</span></button>`
              : ""
          }
        </div>
        ${state.syncProposal ? renderSyncProposal(state.syncProposal) : ""}
      </div>
      <div class="type-editor-section">
        <button data-testid="type-editor-toggle" class="secondary-button type-toggle" type="button">${state.typeEditorOpen ? "Hide" : "Edit"} Task Types</button>
        ${typeEditor}
      </div>
    </article>
  `;
}

function renderSyncProposal(proposal: SyncProposal): string {
  const rows = proposal.preview
    .slice(0, 10)
    .map(
      (event) => `
        <li class="sync-preview-row">
          <time>${escapeHtml(event.time)}</time>
          <span class="block-dot ${cssClass(event.block)}"></span>
          <span>${escapeHtml(event.label)}</span>
        </li>
      `
    )
    .join("");

  return `
    <div class="sync-preview" data-testid="sync-preview">
      ${proposal.summary ? `<p>${escapeHtml(proposal.summary)}</p>` : ""}
      <ol>${rows}</ol>
    </div>
  `;
}

async function addTask(
  root: HTMLElement,
  client: BridgeClient,
  reload: () => Promise<void>
): Promise<void> {
  const description =
    root
      .querySelector<HTMLInputElement>("[data-testid='task-description']")
      ?.value.trim() ?? "";
  const type =
    root.querySelector<HTMLSelectElement>("[data-testid='task-type']")?.value ?? "1";
  const priorityValue =
    root.querySelector<HTMLInputElement>("[data-testid='task-priority']")?.value ?? "5";
  const priority = Number.parseInt(priorityValue, 10);
  await client.send("task_add", { description, type, priority });
  await reload();
}

async function deleteTask(
  button: HTMLButtonElement,
  client: BridgeClient,
  reload: () => Promise<void>
): Promise<void> {
  const description = button.dataset.description ?? "";
  await client.send("task_delete", { description });
  await reload();
}

async function addDeadline(
  root: HTMLElement,
  client: BridgeClient,
  reload: () => Promise<void>
): Promise<void> {
  const event =
    root.querySelector<HTMLInputElement>("[data-testid='deadline-event']")?.value.trim() ??
    "";
  const date =
    root.querySelector<HTMLInputElement>("[data-testid='deadline-date']")?.value.trim() ??
    "";
  await client.send("deadline_add", { event, date });
  await reload();
}

async function deleteDeadline(
  button: HTMLButtonElement,
  client: BridgeClient,
  reload: () => Promise<void>
): Promise<void> {
  const event = button.dataset.event ?? "";
  await client.send("deadline_delete", { event });
  await reload();
}

async function markHabits(
  root: HTMLElement,
  client: BridgeClient,
  reload: () => Promise<void>
): Promise<void> {
  const habitIds = Array.from(
    root.querySelectorAll<HTMLInputElement>("[data-testid='habit-check']:checked")
  ).map((checkbox) => checkbox.dataset.habitId ?? "");
  await client.send("habit_mark", { habitIds });
  await reload();
}

async function generateSync(
  root: HTMLElement,
  client: BridgeClient,
  snapshot: Snapshot,
  reload: () => Promise<void>,
  state: AppState
): Promise<void> {
  const feedback =
    root.querySelector<HTMLTextAreaElement>("[data-testid='sync-feedback']")?.value.trim() ??
    "";
  state.syncFeedback = feedback ? [feedback] : [];
  state.syncProposal = await client.send<SyncProposal>("sync_generate", {
    feedback: state.syncFeedback,
  });
  renderSnapshot(root, client, snapshot, reload, state);
}

async function acceptSync(
  client: BridgeClient,
  reload: () => Promise<void>,
  state: AppState
): Promise<void> {
  if (!state.syncProposal) {
    return;
  }
  await client.send("sync_accept", { plan: state.syncProposal.plan });
  state.syncProposal = null;
  state.syncFeedback = [];
  await reload();
}

async function saveTaskTypes(
  root: HTMLElement,
  client: BridgeClient,
  reload: () => Promise<void>
): Promise<void> {
  const rows = root.querySelectorAll<HTMLDivElement>(".type-row");
  const taskTypes: Record<string, string> = {};
  rows.forEach((row) => {
    const keyInput = row.querySelector<HTMLInputElement>("[data-testid='type-key']");
    const nameInput = row.querySelector<HTMLInputElement>("[data-testid='type-name']");
    if (keyInput && nameInput) {
      const key = keyInput.value.trim();
      const name = nameInput.value.trim();
      if (key && name) {
        taskTypes[key] = name;
      }
    }
  });
  await client.send("settings_set_task_types", { taskTypes });
  await reload();
}

function renderHistory(snapshot: Snapshot): string {
  if (!snapshot.history.length) {
    return "";
  }
  const rows = snapshot.history
    .map(
      (item) => `
        <li class="history-row">
          <span>${escapeHtml(item.description)}</span>
          <strong>${item.priority}</strong>
          <time>${escapeHtml(item.duration)}</time>
        </li>
      `
    )
    .join("");

  return `
    <article class="panel history-panel">
      <p class="eyebrow">${historyIcon} Recent Activity</p>
      <ul class="history-list">${rows}</ul>
    </article>
  `;
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function cssClass(value: string | null): string {
  return (value ?? "plain").replaceAll(/[^a-zA-Z0-9_-]/g, "-") || "plain";
}

function renderIcon(
  node: SvgNode,
  overrides: SvgAttrs = {},
  isRoot = true
): string {
  const [tag, attrs, children = []] = node;
  const mergedAttrs: SvgAttrs = {
    ...attrs,
    ...overrides,
    ...(isRoot
      ? {
          "aria-hidden": "true",
          focusable: "false",
          class: "lucide-icon",
        }
      : {}),
  };
  const attrText = Object.entries(mergedAttrs)
    .map(([name, value]) => `${name}="${escapeHtml(String(value))}"`)
    .join(" ");
  const childText = children.map((child) => renderIcon(child, {}, false)).join("");
  return `<${tag} ${attrText}>${childText}</${tag}>`;
}

function runAction(root: HTMLElement, action: () => Promise<void>): void {
  action().catch((error: unknown) => {
    renderError(root, error);
  });
}
