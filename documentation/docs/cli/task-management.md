---
sidebar_position: 3
---

# Task Management Commands

Commands for managing your personal task list with importance levels and smart duplicate handling.

## add

Add a new task or update an existing one with an importance level.

### Syntax
```bash
rmd add "TASK_DESCRIPTION" PRIORITY_LEVEL [TASK_TYPE] [POSTPONE_DAYS]
```

### Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `TASK_DESCRIPTION` | string | Description of the task (quoted if contains spaces) |
| `PRIORITY_LEVEL` | integer | Priority level from 1-10 (higher = more important) |
| `TASK_TYPE` | integer (optional) | Task type ID as configured in `settings.toml` (e.g. 1 for "read papers", 2 for "gym work") |
| `POSTPONE_DAYS` | integer (optional) | Number of days to postpone the daily urgent alarm (e.g. 1 for tomorrow, 2 for two days later) |

### Examples
```bash
# Add basic task (defaults to task type 1)
rmd add "Complete project proposal" 8

# Add task with a specific task type (e.g. 2 for gym work)
rmd add "Go to the gym" 7 2

# Add high-priority task with a specific type and alarm postponed to tomorrow
rmd add "Biology homework" 9 1 1
```

### Interactive Mode
If you run `rmd add` directly without parameters in an interactive terminal, or if you omit some parameters, the system will display a friendly **Task Creator Wizard** panel, guiding you through a couple of quick questions one by one with emojis to complete the task description, priority level, task type, and the optional **postpone days** (to make it a future task whose daily urgent alarm starts later). Press Enter at the postpone prompt to skip it and start the alarm today.

If you are running in a non-interactive environment (such as a script), omitting the required parameters will print an error message and exit with an error code. Any omitted optional parameters (like task type) will fall back to their default values (e.g. task type 1).

### Task List Color Coding & Legend
In `rmd ls`, the color of each task row/priority bar represents the **Task Type** instead of the priority level. A color legend is displayed at the bottom of the task list showing the association between colors and task types configured in `settings.toml`.

### Smart Duplicate Handling
If you add a task with the same description as an existing task, it updates the priority level instead of creating a duplicate:

```bash
# Initial task
rmd add "Buy groceries" 3

# Update importance (no duplicate created)
rmd add "Buy groceries" 6
```

### Show the List After Adding
By default, `rmd add` prints only the add/update confirmation. To always display
the full `rmd ls` task table after a successful add or update, enable this in
`settings.toml`:

```toml
[settings]
show_tasks_after_add = true
```

## rm

Remove one or more tasks by description or ID.

### Syntax
```bash
rmd rm TASK_IDENTIFIER [TASK_IDENTIFIER...]
```

### Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `TASK_IDENTIFIER` | string/integer | Task description (quoted) or task ID number (from `rmd ls`) |

### Examples
```bash
# Remove by description
rmd rm "Buy groceries"

# Remove multiple tasks by description
rmd rm "Call dentist" "Organize desk"

# Remove by task ID
rmd rm 1 2 3
```

## ls

List all tasks sorted by urgency and importance (highest first).

### Syntax
```bash
rmd ls
```

### Examples
```bash
# Basic task list
rmd ls
```

### Procrastinate Tag

At each configured `daily_urgent` / `daily_urgency` time, the reminder service opens a task-by-task popup for high-priority tasks (priority 8-10). For each task:

- Click `Yes` to mark it complete and remove it from `tasks.json`
- Click `No` to keep it and mark it as procrastinated
- Click `Stop` to leave the remaining urgent tasks unchanged

Tasks you mark as **not completed** are recorded in a procrastinate list file:

- `tasks/procrastinate.json` under your `REMINDER_CONFIG_DIR`
- Each entry stores the task description and the first day it was deferred

In `rmd ls`, procrastinated tasks are shown with:

- A `⏳` prefix
- A procrastination age label such as `(deferred today)` or `(3 days overdue)`
- A dim/italic style if deferred today, or a striking bold red style if overdue (1 or more days)

In later urgent-task popups, the reminder also shows how many days the task has already been procrastinated.

When a procrastinated task is complete (`rmd rm`), it is automatically removed from `tasks/procrastinate.json`.

## history

Display recent completed task activities, grouped by calendar day with visual separators.

Each activity shows the task description, its priority level, when it was started (added), when it ended (completed/deleted), and the total duration.

### Syntax
```bash
rmd history [COUNT]
```

### Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `COUNT` | integer (optional) | Number of recent activities to show (default: 5) |

### Examples
```bash
# Show the 5 most recent completed activities
rmd history

# Show the 10 most recent completed activities
rmd history 10

# Show the 3 most recent completed activities
rmd history 3
```

---

# Habit Management Commands

Commands for interacting with your configured daily habits.

## <a name="habits"></a>track

Log completed habits for today. Habits are loaded from `habits.toml`.

### Syntax
```bash
rmd track [HABIT_IDS...]
```

### Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `HABIT_IDS` | array of strings | (Optional) Space-separated list of Habit IDs to mark completed for today. |

### Examples
```bash
# Mark habits 1 and 2 as completed for today
rmd track 1 2

# Open an interactive prompt window to tick off habits
rmd track
```
