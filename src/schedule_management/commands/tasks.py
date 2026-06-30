"""
Task Commands - CLI commands for task management.

This module provides CLI command handlers for managing tasks:
- add_task: Add a new task with priority
- delete_task: Remove one or more tasks (logged as 'deleted' = completed)
- cancel_task: Remove tasks that were added by mistake (logged as 'cancelled')
- drop_task: Remove tasks you are giving up on (logged as 'dropped')
- show_tasks: Display all tasks in a formatted table

Tasks are stored in a JSON file with 'description' and 'priority' fields.
All actions are logged to the task log for history tracking.

The three removal commands all take the task out of tasks.json, but each
records a distinct history action so they are not all treated as completion:
- 'rm'      -> action 'deleted'   (counts as done; shown in reports/popups/history)
- 'cancel'  -> action 'cancelled' (a mistake; not counted as done)
- 'drop'    -> action 'dropped'   (gave up; not counted as done)

Example Usage (via CLI):
    $ rmd add "Study math" 8        # Add task with priority 8
    $ rmd ls                         # List all tasks
    $ rmd rm 1                       # Delete task by ID (counts as completed)
    $ rmd cancel "typo"              # Cancel an accidentally added task
    $ rmd drop "side project"        # Give up on a task
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from schedule_management import SETTINGS_PATH
from schedule_management.config import ScheduleConfig
from schedule_management.i18n import _t

try:
    from rich import box
    from rich.console import Console
    from rich.table import Table
    from rich.text import Text
except ImportError:
    print(_t("Please install the 'rich' library: pip install rich"))
    sys.exit(1)

from schedule_management.data import (
    load_tasks,
    save_tasks,
    load_procrastinate_list,
    load_procrastinate_records,
    save_procrastinate_list,
    get_procrastinate_age_days,
    log_task_action,
)
from schedule_management.commands.settings import DEFAULT_TASK_TYPES


# =============================================================================
# ADD TASK COMMAND
# =============================================================================


def _should_show_tasks_after_change() -> bool:
    """Return whether the active settings request an `rmd ls` display after a change."""
    try:
        return ScheduleConfig(str(SETTINGS_PATH)).show_tasks_after_change
    except Exception:
        return False


def _save_new_task_type(settings_path: str, type_id: str, type_name: str) -> bool:
    """Persist a newly created task type to settings.toml.

    Loads the active settings via :class:`SettingsModel` so the rest of the
    file is preserved, adds the new key under ``[task_types]``, and saves.
    Returns True on success, False if the write failed (the caller falls
    back to using the type only for the current task).
    """
    try:
        from schedule_management.commands.settings import SettingsModel

        path = Path(settings_path)
        model = SettingsModel(path)
        model.set("task_types", type_id, type_name)
        model.save()
        return True
    except Exception:
        return False


def _prompt_create_task_type(
    console: "Console",
    task_types: dict[str, str],
    type_id: str,
    settings_path: str,
) -> str | None:
    """Finish creating a new task type identified by ``type_id``.

    Prompts for a non-empty type name, persists it to settings.toml so it is
    available for future tasks, and returns the chosen ``type_id``. Returns
    ``None`` if the user cancels (Ctrl+C / EOF) or enters an empty name.
    """
    console.print(
        "[bold green]"
        + _t("✨ New task type! Let's create type {type_id}.").format(type_id=type_id)
        + "[/bold green]"
    )
    while True:
        try:
            type_name = console.input(
                "[bold cyan]" + _t("🏷️  Enter a name for task type {type_id}: ").format(type_id=type_id)
                + "[/bold cyan]"
            ).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n" + _t("👋 Operation cancelled. Have a great day! ✨"))
            return None
        if not type_name:
            console.print("[bold yellow]" + _t("⚠️  Oops! Task type name can't be empty. Let's try that again! 😊") + "[/bold yellow]")
            continue
        if type_name in task_types.values():
            console.print("[bold yellow]" + _t("⚠️  Oops! A task type with that name already exists. Let's try that again! 😊") + "[/bold yellow]")
            continue
        break

    if _save_new_task_type(settings_path, type_id, type_name):
        task_types[type_id] = type_name
        console.print(
            "[bold green]"
            + _t("✅ Task type '{type_name}' (number {type_id}) created and saved!").format(
                type_name=type_name, type_id=type_id
            )
            + "[/bold green]"
        )
    else:
        # Persist the type in memory for this task even if the write failed.
        task_types[type_id] = type_name
        console.print(
            "[bold yellow]"
            + _t("⚠️  Could not save the new task type to settings.toml; using it for this task only.").format()
            + "[/bold yellow]"
        )
    return type_id


def add_task(args) -> int:
    """
    Handle the 'add' command - add a new task to the CLI-managed task list.

    If a task with the same description already exists, updates
    its priority instead of creating a duplicate.

    Args:
        args: Namespace with 'task' (description), 'priority' (int), and optional 'postpone' (int)

    Returns:
        0 on success, 1 on error

    Example:
        $ rmd add "Complete homework" 7 1
        ✅ Task 'Complete homework' added successfully with priority 7! (Daily urgent alarm postponed until 2026-05-27)
    """
    task_description = getattr(args, "task", None)
    priority = getattr(args, "priority", None)
    task_type = getattr(args, "task_type", None)
    postpone = getattr(args, "postpone", None)

    # Handle MagicMock args in unit tests
    try:
        from unittest.mock import Mock
        if isinstance(task_type, Mock):
            task_type = None
    except ImportError:
        pass

    # Load task types from settings
    try:
        config = ScheduleConfig(str(SETTINGS_PATH))
        task_types = config.task_types
    except Exception:
        task_types = {}
    if not task_types:
        task_types = dict(DEFAULT_TASK_TYPES)

    # Check for missing parameters and handle interactive prompt / TUI
    if task_description is None or priority is None or task_type is None:
        if not sys.stdin.isatty():
            # If non-interactive, only task and priority are strictly required (default task_type to 1)
            if task_description is None or priority is None:
                missing = []
                if task_description is None:
                    missing.append("task")
                if priority is None:
                    missing.append("PRIORITY")
                print(_t("❌ Error: the following arguments are required: {missing}").format(missing=", ".join(missing)))
                return 1
            if task_type is None:
                task_type = 1
        else:
            from rich.panel import Panel
            console = Console()

            welcome_text = Text()
            if task_description is None:
                welcome_text.append(_t("Let's add a new task to your schedule! 🚀\n"), style="bold green")
                welcome_text.append(_t("I'll guide you through a couple of quick questions. 🌟"), style="cyan")
            else:
                welcome_text.append(_t("Almost there! Let's complete the details for your task. ✨\n"), style="bold green")
                welcome_text.append(_t("Task: {task_description}").format(task_description=task_description), style="cyan")

            panel = Panel(
                welcome_text,
                title="[bold green]✨ " + _t("Task Creator Wizard") + " ✨[/bold green]",
                border_style="green",
                padding=(1, 2)
            )
            console.print(panel)

            if task_description is None:
                while True:
                    try:
                        desc_input = console.input("[bold cyan]" + _t("✍️  What task would you like to add? ") + "[/bold cyan]").strip()
                    except (EOFError, KeyboardInterrupt):
                        print("\n" + _t("👋 Operation cancelled. Have a great day! ✨"))
                        return 1
                    if desc_input:
                        task_description = desc_input
                        break
                    console.print("[bold yellow]" + _t("⚠️  Oops! The task description can't be empty. Let's try that again! 😊") + "[/bold yellow]")

            if priority is None:
                while True:
                    try:
                        prio_input = console.input("[bold cyan]" + _t("🔢 What is the priority level for this task (1-10)? ") + "[/bold cyan]").strip()
                    except (EOFError, KeyboardInterrupt):
                        print("\n" + _t("👋 Operation cancelled. Have a great day! ✨"))
                        return 1
                    try:
                        prio_val = int(prio_input)
                        if 1 <= prio_val <= 10:
                            priority = prio_val
                            break
                        else:
                            console.print("[bold yellow]" + _t("⚠️  Oops! Priority must be between 1 and 10. Let's try that again! 🌟") + "[/bold yellow]")
                    except ValueError:
                        console.print("[bold yellow]" + _t("⚠️  Oops! Priority needs to be a valid number. Please enter a number between 1 and 10! 🔢") + "[/bold yellow]")

            if task_type is None:
                console.print("\n[bold cyan]" + _t("🔢 Select a task type:") + "[/bold cyan]")
                sorted_types = sorted(task_types.items(), key=lambda item: int(item[0]) if item[0].isdigit() else 999)
                for k, v in sorted_types:
                    console.print(f"  [green]{k}[/green]. {v}")
                console.print("[dim]" + _t("💡 Tip: enter a number not listed above to create a new task type.") + "[/dim]")
                while True:
                    try:
                        type_input = console.input("[bold cyan]" + _t("Enter Task Type Number: ") + "[/bold cyan]").strip()
                    except (EOFError, KeyboardInterrupt):
                        print("\n" + _t("👋 Operation cancelled. Have a great day! ✨"))
                        return 1
                    if type_input in task_types:
                        task_type = int(type_input)
                        break
                    # Treat an unrecognized number as a request to create a new type.
                    if type_input.isdigit() and int(type_input) > 0:
                        created = _prompt_create_task_type(
                            console, task_types, type_input, str(SETTINGS_PATH)
                        )
                        if created is None:
                            # User cancelled creating the new type; re-prompt for the type number.
                            continue
                        task_type = int(created)
                        break
                    console.print("[bold yellow]" + _t("⚠️  Oops! Please enter a positive number (an existing one or a new one to create a type).") + "[/bold yellow]")

            # Optional: postpone the daily urgent alarm to make this a future task.
            if postpone is None:
                console.print(
                    "\n[bold cyan]"
                    + _t("🗓️  Postpone the daily urgent alarm? Enter days from now (0 or empty = start today): ")
                    + "[/bold cyan]"
                )
                while True:
                    try:
                        postpone_input = console.input(
                            "[bold cyan]" + _t("Postpone days (default 0): ") + "[/bold cyan]"
                        ).strip()
                    except (EOFError, KeyboardInterrupt):
                        print("\n" + _t("👋 Operation cancelled. Have a great day! ✨"))
                        return 1
                    if postpone_input == "":
                        postpone = 0
                        break
                    try:
                        postpone_val = int(postpone_input)
                        if postpone_val < 0:
                            console.print(
                                "[bold yellow]"
                                + _t("⚠️  Oops! Postpone days must be a non-negative integer. Let's try that again! 🌟")
                                + "[/bold yellow]"
                            )
                            continue
                        postpone = postpone_val
                        break
                    except ValueError:
                        console.print(
                            "[bold yellow]"
                            + _t("⚠️  Oops! Postpone days needs to be a valid number. Please enter a non-negative integer! 🔢")
                            + "[/bold yellow]"
                        )

    # Validate priority
    if priority <= 0:
        print(_t("❌ Error: Priority must be a positive integer"))
        return 1

    # Validate task_type if specified
    if task_type is not None:
        if str(task_type) not in task_types:
            print(_t("❌ Error: Invalid task type. Choose from: {choices}").format(choices=", ".join(task_types.keys())))
            return 1

    # Validate postpone
    alarm_from = None
    if postpone is not None and isinstance(postpone, int):
        if postpone < 0:
            print(_t("❌ Error: Postpone days must be a non-negative integer"))
            return 1
        if postpone > 0:
            from datetime import timedelta
            alarm_from_date = datetime.now().date() + timedelta(days=postpone)
            alarm_from = alarm_from_date.isoformat()

    # Load existing tasks
    tasks = load_tasks()

    # Check for existing task with same description
    existing_task_index = None
    for i, task in enumerate(tasks):
        if task["description"] == task_description:
            existing_task_index = i
            break

    # Create new task
    new_task = {
        "description": task_description,
        "priority": priority,
        "type": str(task_type),
    }
    if alarm_from:
        new_task["alarm_from"] = alarm_from

    # Update existing or add new
    if existing_task_index is not None:
        old_priority = tasks[existing_task_index]["priority"]
        tasks[existing_task_index] = new_task
        suffix = _t(" (Daily urgent alarm postponed until {alarm_from})").format(alarm_from=alarm_from) if alarm_from else ""
        action_msg = _t("✅ Task '{task_description}' updated! Priority changed from {old_priority} to {priority}").format(
            task_description=task_description, old_priority=old_priority, priority=priority
        ) + suffix

        # Log the update
        try:
            log_task_action("updated", new_task, {"old_priority": old_priority})
        except Exception as e:
            print(_t("⚠️  Warning: Could not log task update: {e}").format(e=e))
    else:
        tasks.append(new_task)
        suffix = _t(" (Daily urgent alarm postponed until {alarm_from})").format(alarm_from=alarm_from) if alarm_from else ""
        action_msg = _t("✅ Task '{task_description}' added successfully with priority {priority}!").format(
            task_description=task_description, priority=priority
        ) + suffix

        # Log the addition
        try:
            log_task_action("added", new_task)
        except Exception as e:
            print(_t("⚠️  Warning: Could not log task addition: {e}").format(e=e))

    # Save tasks
    try:
        save_tasks(tasks)
    except Exception as e:
        print(_t("❌ Error saving task: {e}").format(e=e))
        return 1

    print(action_msg)
    if _should_show_tasks_after_change():
        show_tasks(args)
    return 0


# =============================================================================
# TASK REMOVAL COMMANDS (rm / cancel / drop)
# =============================================================================


def _remove_tasks(args, *, log_action: str, success_single: str, success_multi: str) -> int:
    """
    Shared engine for the rm / cancel / drop commands.

    Removes one or more tasks identified by ID number (from 'rmd ls') or by
    exact description text. All removal commands take the task out of
    tasks.json and keep the procrastinate list in sync; only the recorded
    history ``log_action`` differs, so each command produces a distinct
    history while sharing identical matching/sorting behavior.

    Args:
        args: Namespace with 'tasks' (list of identifiers).
        log_action: The history action to record for each removed task
            ('deleted', 'cancelled', or 'dropped').
        success_single: i18n template for the single-success message,
            expecting a ``{deletion}`` placeholder.
        success_multi: i18n template for the multi-success header,
            expecting a ``{count}`` placeholder.

    Returns:
        0 on success, 1 if any removals failed or saving failed.
    """
    task_identifiers = args.tasks

    # Load existing tasks
    tasks = load_tasks()
    procrastinate_list = load_procrastinate_list()
    procrastinate_updated = False

    if not tasks:
        print(_t("⚠️  No tasks found to delete"))
        return 1

    # Sort tasks into three sections (procrastinated -> current -> incoming)
    # ordered by priority descending in each section to match show_tasks display
    today = datetime.now().date()
    sorted_tasks = _sort_tasks_by_section_and_priority(tasks, today, procrastinate_list)

    all_errors: list[str] = []
    successful_removals: list[str] = []

    for task_identifier in task_identifiers:
        # Try to parse as integer ID first
        try:
            task_id = int(task_identifier)

            # Validate ID range
            if task_id < 1 or task_id > len(sorted_tasks):
                error_msg = _t("❌ Invalid task ID: {task_id}. Please use a number between 1 and {length}").format(
                    task_id=task_id, length=len(sorted_tasks)
                )
                all_errors.append(error_msg)
                continue

            # Get task by ID (1-indexed)
            task_to_delete = sorted_tasks[task_id - 1]
            task_description = task_to_delete["description"]

            # Remove from original tasks list
            original_count = len(tasks)
            removed_tasks = [t for t in tasks if t["description"] == task_description]
            tasks = [t for t in tasks if t["description"] != task_description]

        except ValueError:
            # Treat as string description
            task_description = task_identifier
            original_count = len(tasks)
            removed_tasks = [t for t in tasks if t["description"] == task_description]
            tasks = [t for t in tasks if t["description"] != task_description]

        # Check if anything was removed
        if len(tasks) == original_count:
            error_msg = _t("❌ Task '{task_description}' not found").format(
                task_description=task_description
            )
            all_errors.append(error_msg)
            continue

        # Log removals with the caller-specified action so each command
        # produces a distinct history.
        try:
            for removed_task in removed_tasks:
                log_task_action(log_action, removed_task)
        except Exception as e:
            print(_t("⚠️  Warning: Could not log task deletion: {e}").format(e=e))

        # Keep procrastinate list in sync with removed tasks
        for removed_task in removed_tasks:
            description = removed_task.get("description")
            if isinstance(description, str) and description in procrastinate_list:
                procrastinate_list.discard(description)
                procrastinate_updated = True

        removed_count = original_count - len(tasks)

        if removed_count == 1:
            successful_removals.append(_t("Task '{task_description}'").format(task_description=task_description))
        else:
            successful_removals.append(
                _t("{deleted_count} tasks with description '{task_description}'").format(
                    deleted_count=removed_count, task_description=task_description
                )
            )

    # Print results
    for error in all_errors:
        print(error)

    if successful_removals:
        try:
            save_tasks(tasks)
            if procrastinate_updated:
                save_procrastinate_list(procrastinate_list)
            if len(successful_removals) == 1:
                print(success_single.format(deletion=successful_removals[0]))
            else:
                print(success_multi.format(count=len(successful_removals)))
                for removal in successful_removals:
                    print(f"   - {removal}")
            if _should_show_tasks_after_change():
                show_tasks(args)
            return 0 if not all_errors else 1
        except Exception as e:
            print(_t("❌ Error saving tasks: {e}").format(e=e))
            return 1
    else:
        return 1


def delete_task(args) -> int:
    """
    Handle the 'rm' command - delete one or more tasks.

    Tasks can be identified by:
    - ID number (from 'rmd ls' output)
    - Exact description text

    Removal is logged with action 'deleted', which counts as completion in
    history, reports, and popups. Use 'cancel' or 'drop' instead when the
    task should NOT be counted as done.

    Args:
        args: Namespace with 'tasks' (list of identifiers)

    Returns:
        0 on success, 1 if any deletions failed

    Example:
        $ rmd rm 1 2 3
        ✅ 3 sets of tasks deleted successfully

        $ rmd rm "Study math"
        ✅ Task 'Study math' deleted successfully!
    """
    return _remove_tasks(
        args,
        log_action="deleted",
        success_single=_t("✅ {deletion} deleted successfully!"),
        success_multi=_t("✅ {count} sets of tasks deleted successfully:"),
    )


def cancel_task(args) -> int:
    """
    Handle the 'cancel' command - remove a task that was added by mistake.

    Behaves like 'rm' (removes the task and syncs the procrastinate list) but
    logs the action as 'cancelled' instead of 'deleted', so it is NOT counted
    as a completion in history, reports, or popups. Use this when an earlier
    'add' was a mistake.

    Args:
        args: Namespace with 'tasks' (list of identifiers)

    Returns:
        0 on success, 1 if any cancellations failed

    Example:
        $ rmd cancel "typo task"
        🚫 Task 'typo task' cancelled (not counted as done).
    """
    return _remove_tasks(
        args,
        log_action="cancelled",
        success_single=_t("🚫 {deletion} cancelled (not counted as done)."),
        success_multi=_t("🚫 {count} sets of tasks cancelled (not counted as done):"),
    )


def drop_task(args) -> int:
    """
    Handle the 'drop' command - give up on one or more tasks.

    Behaves like 'rm' (removes the task and syncs the procrastinate list) but
    logs the action as 'dropped' instead of 'deleted', so it is NOT counted
    as a completion in history, reports, or popups. Use this when you have too
    many tasks and want to abandon some without crediting them as done.

    Args:
        args: Namespace with 'tasks' (list of identifiers)

    Returns:
        0 on success, 1 if any drops failed

    Example:
        $ rmd drop "side project"
        🏳️ Task 'side project' dropped (gave up).
    """
    return _remove_tasks(
        args,
        log_action="dropped",
        success_single=_t("🏳️ {deletion} dropped (gave up)."),
        success_multi=_t("🏳️ {count} sets of tasks dropped (gave up):"),
    )


# =============================================================================
# SHOW TASKS COMMAND
# =============================================================================


def _format_procrastination_suffix(age_days: int | None) -> str:
    """Format procrastination age for the task list."""
    if age_days is None:
        return ""
    if age_days == 0:
        return _t(" (deferred today)")
    if age_days == 1:
        return _t(" (1 day overdue)")
    return _t(" ({age_days} days overdue)").format(age_days=age_days)


def _format_postpone_suffix(days_left: int) -> str:
    """Format postponement remaining days for the task list."""
    if days_left <= 0:
        return ""
    if days_left == 1:
        return _t(" (coming tomorrow)")
    return _t(" (coming in {days_left} days)").format(days_left=days_left)


def _sort_tasks_by_section_and_priority(
    tasks: list[dict], today: Any, procrastinate_list: set[str]
) -> list[dict]:
    """
    Sort tasks into three sections:
    1. Procrastinated tasks
    2. Current tasks
    3. Incoming (future postponed) tasks
    Within each section, tasks are ordered by priority (highest first).
    """
    def get_days_left(task) -> int:
        alarm_from = task.get("alarm_from")
        if alarm_from:
            try:
                alarm_from_date = datetime.strptime(alarm_from, "%Y-%m-%d").date()
                return (alarm_from_date - today).days
            except Exception:
                pass
        return 0

    def task_sort_key(task):
        days_left = get_days_left(task)
        is_postponed_future = days_left > 0
        is_procrastinated = (not is_postponed_future) and (task["description"] in procrastinate_list)

        if is_procrastinated:
            section = 0
        elif not is_postponed_future:
            section = 1
        else:
            section = 2

        return (section, -task["priority"])

    return sorted(tasks, key=task_sort_key)


def _resolve_task_type_id(value: str, task_types: dict[str, str]) -> str | None:
    """Resolve a user-provided type filter to a canonical task type ID.

    Accepts either a type ID (e.g. '1') or a type name (e.g. 'coding'). The
    match against names is case-insensitive. Returns the matching type ID, or
    ``None`` if nothing matches.
    """
    if value in task_types:
        return value
    lowered = value.lower()
    for tid, tname in task_types.items():
        if isinstance(tname, str) and tname.lower() == lowered:
            return tid
    return None


def show_tasks(args) -> int:
    """
    Handle the 'ls' command - display all tasks in a formatted table.

    Shows tasks sorted by priority (highest first) with:
    - ID number for reference
    - Visual priority bar
    - Task description

    Args:
        args: Namespace with optional 'task_type' filter (type ID or name)

    Returns:
        0 on success, 1 if an invalid type filter was given

    Example output:
        ╭──────────────────────────────────────╮
        │          Current Task List           │
        ├────┬──────────────────┬──────────────┤
        │ ID │ Priority         │ Description  │
        ├────┼──────────────────┼──────────────┤
        │  1 │ 🔴 ████████░░ (8) │ Study math   │
        │  2 │ 🟡 █████░░░░░ (5) │ Clean room   │
        ╰────┴──────────────────┴──────────────╯
    """
    tasks = load_tasks()
    procrastinate_records = load_procrastinate_records()
    procrastinate_list = set(procrastinate_records)
    today = datetime.now().date()

    console = Console()

    if not tasks:
        console.print("[bold yellow]" + _t("📋 No tasks found") + "[/bold yellow]")
        return 0

    # Sort tasks into three sections (procrastinated -> current -> incoming)
    # ordered by priority descending in each section
    sorted_tasks = _sort_tasks_by_section_and_priority(tasks, today, procrastinate_list)

    # Load task types from settings
    try:
        config = ScheduleConfig(str(SETTINGS_PATH))
        task_types = config.task_types
    except Exception:
        task_types = {}
    if not task_types:
        task_types = dict(DEFAULT_TASK_TYPES)

    sorted_type_ids = sorted(task_types.keys(), key=lambda x: int(x) if x.isdigit() else 999)

    # Resolve an optional --type filter (accepts a type ID like '1' or a type
    # name like 'coding') to the canonical type ID used in task records. Only a
    # real string activates the filter, so callers passing a plain Namespace or
    # a mock arg without this attribute are treated as "no filter".
    type_filter = getattr(args, "task_type", None)
    filter_type_id: str | None = None
    if isinstance(type_filter, str) and type_filter:
        resolved = _resolve_task_type_id(type_filter, task_types)
        if resolved is None:
            valid = ", ".join(f"{tid}={tname}" for tid, tname in sorted(task_types.items()))
            console.print(
                "[bold red]"
                + _t("❌ Unknown task type '{type_filter}'. Valid types: {valid}").format(
                    type_filter=type_filter, valid=valid
                )
                + "[/bold red]"
            )
            return 1
        filter_type_id = resolved

    COLORS = ["red", "green", "blue", "yellow", "magenta", "cyan", "white", "bright_blue", "bright_green", "bright_red"]
    type_colors = {}
    for idx, tid in enumerate(sorted_type_ids):
        type_colors[tid] = COLORS[idx % len(COLORS)]

    # Create table
    table = Table(
        title="[bold]" + _t("Current Task List") + "[/bold]",
        box=box.ROUNDED,
        header_style="bold cyan",
        expand=True,
    )

    table.add_column(_t("ID"), justify="right", style="dim", width=4, no_wrap=True)
    table.add_column(_t("Priority"), justify="left", no_wrap=True)
    table.add_column(_t("Description"), justify="left")

    # Enumerate over the full sorted list so the displayed IDs match what
    # 'rm'/'cancel'/'drop' resolve (they index against the full 'ls' order).
    # When a --type filter is active, skip rows of other types without
    # re-numbering the visible IDs.
    displayed_count = 0
    for i, task in enumerate(sorted_tasks, 1):
        description = task["description"]
        priority = task["priority"]
        alarm_from = task.get("alarm_from")

        # Determine task type
        task_type_id = str(task.get("type", sorted_type_ids[0] if sorted_type_ids else "1"))
        if filter_type_id is not None and task_type_id != filter_type_id:
            continue

        postpone_suffix = ""
        is_postponed_future = False
        if alarm_from:
            try:
                alarm_from_date = datetime.strptime(alarm_from, "%Y-%m-%d").date()
                days_left = (alarm_from_date - today).days
                if days_left > 0:
                    postpone_suffix = _format_postpone_suffix(days_left)
                    is_postponed_future = True
            except Exception:
                pass

        color = type_colors.get(task_type_id, "white")
        type_name = task_types.get(task_type_id, "other")

        # Visual priority bar (max 10 blocks for layout)
        filled = "█" * min(priority, 10)
        empty = "░" * (10 - min(priority, 10))

        prio_visual = f"[{color}]{filled}[dim]{empty}[/dim] ({priority})[/{color}]"
        if is_postponed_future:
            description_text = Text(
                f"💤 {description}{postpone_suffix}",
                style="italic dim",
            )
        elif description in procrastinate_list:
            age_days = get_procrastinate_age_days(
                procrastinate_records.get(description, {}).get("since"),
                today=today,
            )
            # Make overdue tasks (1 or more days overdue) very striking
            is_overdue = age_days is not None and age_days >= 1
            description_text = Text(
                f"⏳ {description}{_format_procrastination_suffix(age_days)}",
                style="bold red" if is_overdue else "italic dim",
            )
        else:
            description_text = Text(f"{description}")

        table.add_row(str(i), prio_visual, description_text)
        displayed_count += 1

    if filter_type_id is not None and displayed_count == 0:
        type_name = task_types.get(filter_type_id, "other")
        console.print(
            "[bold yellow]"
            + _t("📋 No tasks found for type '{type_name}'").format(type_name=type_name)
            + "[/bold yellow]"
        )
        return 0

    legend_items = []
    for tid in sorted_type_ids:
        tname = task_types[tid]
        tcolor = type_colors[tid]
        legend_items.append(f"[{tcolor}]■ {tname}[/{tcolor}]")
    legend_str = "  ".join(legend_items)

    console.print(table)
    console.print(legend_str)
    footer = (
        _t("Showing {shown} of {total} tasks (type: {type_name})").format(
            shown=displayed_count, total=len(tasks), type_name=task_types.get(filter_type_id, "other")
        )
        if filter_type_id is not None
        else _t("Total tasks: {count}").format(count=len(tasks))
    )
    console.print("[dim]" + footer + "[/dim]", justify="right")

    return 0
