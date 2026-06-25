"""
Platform Utilities - Cross-platform detection and interaction functions.

This module provides platform-agnostic functions for:
- Platform detection (macOS, Linux, Windows)
- Sound playback using native audio systems
- Dialog/notification display using native UI frameworks
- Multi-select and Yes/No prompt dialogs

Supported Platforms:
- macOS: Uses afplay for sound, osascript/AppleScript for dialogs
- Linux: Uses paplay/aplay for sound, zenity/kdialog for dialogs
- Windows: Limited support (detection only)

Example Usage:
    >>> from schedule_management.platform import get_platform, play_sound, show_dialog
    >>> platform = get_platform()  # Returns 'macos', 'linux', 'windows', or 'unknown'
    >>> play_sound('/path/to/sound.aiff')
    >>> show_dialog('Reminder: Time for a break!')
"""

import shutil
import subprocess
import sys
from pathlib import Path


# =============================================================================
# PLATFORM DETECTION
# =============================================================================


def get_platform() -> str:
    """
    Detect the current operating system platform.

    Returns:
        str: One of 'macos', 'linux', 'windows', or 'unknown'

    Example:
        >>> platform = get_platform()
        >>> if platform == 'macos':
        ...     # macOS-specific code
        ...     pass
    """
    platform_id = sys.platform.lower()
    if platform_id == "darwin":
        return "macos"
    elif platform_id.startswith("linux"):
        return "linux"
    elif platform_id.startswith("win"):
        return "windows"
    else:
        return "unknown"


def open_file(path: str | Path) -> bool:
    """
    Open a file or directory using the platform's default application.

    Picks the native "open" command for the current platform and falls back
    silently if no suitable opener is found.

    Args:
        path: File or directory path to open.

    Returns:
        True if an opener command was available and launched, False otherwise.
        Note: a True result does not guarantee the application actually opened
        the file; the opener process is spawned non-blocking.

    Example:
        >>> open_file('/path/to/report.pdf')
    """
    platform_name = get_platform()
    if platform_name == "macos":
        openers = ["open"]
    elif platform_name == "linux":
        openers = ["xdg-open"]
    else:
        openers = ["xdg-open", "open"]

    for opener in openers:
        if shutil.which(opener) is None:
            continue
        try:
            subprocess.Popen([opener, str(path)])
            return True
        except (FileNotFoundError, OSError):
            continue
    return False


# =============================================================================
# SOUND PLAYBACK
# =============================================================================


def play_sound_macos(sound_file: str) -> None:
    """
    Play a sound file on macOS using the afplay command.

    Args:
        sound_file: Path to the audio file (typically .aiff or .mp3)

    Note:
        Runs asynchronously using Popen, so the function returns immediately.
    """
    subprocess.Popen(["afplay", sound_file])


def play_sound_linux(sound_file: str) -> None:
    """
    Play a sound file on Linux using available audio backends.

    Tries multiple audio systems in order:
    1. paplay (PulseAudio)
    2. aplay (ALSA)
    3. play (SoX)

    Args:
        sound_file: Path to the audio file

    Note:
        Falls back to next backend if current one is not available.
    """
    for cmd in [["paplay", sound_file], ["aplay", sound_file], ["play", sound_file]]:
        try:
            subprocess.Popen(cmd, stderr=subprocess.DEVNULL)
            return
        except FileNotFoundError:
            continue
    print(f"Warning: Could not play sound {sound_file}")


def play_sound(sound_file: str) -> None:
    """
    Play a sound file using the appropriate system audio backend.

    Automatically detects the platform and uses the appropriate
    sound playback method.

    Args:
        sound_file: Path to the audio file to play

    Example:
        >>> play_sound('/System/Library/Sounds/Ping.aiff')
    """
    platform_name = get_platform()
    if platform_name == "macos":
        play_sound_macos(sound_file)
    elif platform_name == "linux":
        play_sound_linux(sound_file)
    else:
        print(f"Sound playback not supported on {platform_name}")


# =============================================================================
# DIALOG DISPLAY
# =============================================================================


def _escape_applescript_string(value: str) -> str:
    """
    Escape special characters for use in AppleScript strings.

    Args:
        value: The string to escape

    Returns:
        Escaped string safe for AppleScript
    """
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def _show_tk_dialog(
    message: str,
    buttons: list[str],
    default_button: str,
    title: str = "Reminder",
    timeout: int | None = None,
) -> str | None:
    """
    Show a modal dialog using tkinter with a readable font size.

    Falls back to AppleScript ``display dialog`` when tkinter is unavailable.

    Args:
        message: The message to display (may contain newlines).
        buttons: Button labels in display order.
        default_button: Label of the button highlighted as the default action.
        title: Window title.
        timeout: Auto-close after this many seconds (``None`` to disable).

    Returns:
        The label of the button that was clicked, or ``None`` if the window
        was closed without a selection.
    """
    try:
        import tkinter as tk
        from tkinter import font as tkfont
    except ImportError:
        return None

    result: dict[str, str | None] = {"clicked": None}

    root = tk.Tk()
    root.withdraw()

    dialog = tk.Toplevel(root)
    dialog.title(title)
    dialog.resizable(False, False)
    dialog.attributes("-topmost", True)
    dialog.protocol("WM_DELETE_WINDOW", lambda: _click(None))

    def _click(label: str | None) -> None:
        result["clicked"] = label
        dialog.destroy()
        root.quit()

    message_font = tkfont.Font(family="Helvetica", size=16)
    button_font = tkfont.Font(family="Helvetica", size=13)

    msg_label = tk.Label(
        dialog, text=message, font=message_font, justify="left", padx=24, pady=20
    )
    msg_label.pack(fill="both", expand=True)

    btn_frame = tk.Frame(dialog)
    btn_frame.pack(fill="x", padx=24, pady=(0, 16))

    for label in buttons:
        btn = tk.Button(
            btn_frame,
            text=label,
            font=button_font,
            width=14,
            command=lambda l=label: _click(l),
        )
        btn.pack(side="right", padx=4)
        if label == default_button:
            dialog.bind("<Return>", lambda _e, l=label: _click(l))
            btn.focus_set()

    dialog.bind("<Escape>", lambda _e: _click(None))

    dialog.update_idletasks()
    dialog.transient()
    dialog.grab_set()

    dialog.update_idletasks()
    sw = dialog.winfo_screenwidth()
    sh = dialog.winfo_screenheight()
    x = (sw - dialog.winfo_width()) // 2
    y = (sh - dialog.winfo_height()) // 2
    dialog.geometry(f"+{x}+{y}")

    if timeout is not None:
        dialog.after(timeout * 1000, lambda: _click(default_button))

    root.mainloop()
    return result["clicked"]


def show_dialog_macos(message: str) -> str:
    """
    Show a modal dialog with a dismiss button on macOS.

    Uses a tkinter dialog with a large font so the message is easy to read.
    Falls back to AppleScript when tkinter is unavailable.

    Args:
        message: The message to display in the dialog

    Returns:
        The button clicked ('停止闹铃' typically)
    """
    button_label = "停止闹铃"
    clicked = _show_tk_dialog(
        message,
        buttons=[button_label],
        default_button=button_label,
    )
    if clicked is not None:
        return clicked
    escaped = _escape_applescript_string(message)
    result = subprocess.run(
        [
            "osascript",
            "-e",
            f'display dialog "{escaped}" buttons {{"{button_label}"}} default button "{button_label}"',
        ],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() or button_label


def show_dialog_linux(message: str) -> str:
    """
    Show a dialog on Linux using available desktop notification systems.

    Tries multiple backends in order:
    1. zenity (GNOME)
    2. kdialog (KDE)
    3. notify-send (generic desktop notifications)

    Args:
        message: The message to display

    Returns:
        'OK' if dialog was shown successfully, 'Cancel' otherwise
    """
    for cmd_template in [
        ["zenity", "--info", "--text={}"],
        ["kdialog", "--msgbox", "{}"],
        ["notify-send", "--urgency=critical", "Reminder", "{}"],
    ]:
        try:
            cmd = [arg.format(message) if "{}" in arg else arg for arg in cmd_template]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return "OK" if result.returncode == 0 else "Cancel"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    print(f"Warning: Could not show dialog: {message}")
    return "OK"


def show_dialog(message: str) -> str:
    """
    Show a dialog/notification using the platform's native UI.

    Args:
        message: The message to display

    Returns:
        The button clicked or 'OK' on success

    Example:
        >>> result = show_dialog('Time for a break!')
    """
    platform_name = get_platform()
    if platform_name == "macos":
        return show_dialog_macos(message)
    elif platform_name == "linux":
        return show_dialog_linux(message)
    else:
        print(f"Dialog display not supported on {platform_name}")
        return "OK"


# =============================================================================
# MULTI-SELECT DIALOG
# =============================================================================


def choose_multiple(options: list[str], title: str, prompt: str) -> list[str] | None:
    """
    Prompt the user with a GUI multi-select list.

    Opens a native dialog allowing the user to select multiple items
    from a list using checkboxes or multi-selection.

    Args:
        options: List of option strings to display
        title: Dialog window title
        prompt: Instructions shown above the option list

    Returns:
        - list[str]: Selected option strings (may be empty if none selected)
        - None: User cancelled OR no supported GUI backend is available

    Example:
        >>> habits = ['Exercise', 'Read', 'Meditate']
        >>> selected = choose_multiple(habits, 'Habit Tracker', 'Select completed habits:')
        >>> if selected is not None:
        ...     print(f'Completed: {selected}')

    Platform Support:
        - macOS: Uses AppleScript 'choose from list'
        - Linux: Uses zenity checklist dialog
    """
    platform_name = get_platform()

    if platform_name == "macos":
        # Build AppleScript for multi-select list
        escaped_items = ",".join(
            f'"{_escape_applescript_string(item)}"' for item in options
        )
        script = f"""
set optionsList to {{{escaped_items}}}
set promptText to "{_escape_applescript_string(prompt)}"
set titleText to "{_escape_applescript_string(title)}"
set choice to choose from list optionsList with title titleText with prompt promptText with multiple selections allowed
if choice is false then
  return "__CANCEL__"
end if
set AppleScript's text item delimiters to "\\n"
return choice as text
""".strip()
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=120,
            )
        except FileNotFoundError:
            print("Warning: osascript not found; cannot show habit prompt window.")
            return None
        except subprocess.TimeoutExpired:
            print("Warning: habit prompt window timed out.")
            return None

        if result.returncode != 0:
            return None
        stdout = (result.stdout or "").strip()
        if stdout == "__CANCEL__":
            return None
        if not stdout:
            return []
        return [line for line in stdout.splitlines() if line.strip()]

    if platform_name == "linux":
        # Use zenity checklist for Linux
        zenity_cmd = [
            "zenity",
            "--list",
            "--checklist",
            "--title",
            title,
            "--text",
            prompt,
        ]
        zenity_cmd += ["--column", "Done", "--column", "Habit"]
        for option in options:
            zenity_cmd += ["FALSE", option]
        try:
            result = subprocess.run(
                zenity_cmd + ["--separator", "\n"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                return None
            stdout = (result.stdout or "").strip()
            if not stdout:
                return []
            return [line for line in stdout.splitlines() if line.strip()]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None

    return None


# =============================================================================
# YES/NO DIALOG
# =============================================================================


def ask_yes_no_macos(question: str, title: str) -> bool | None:
    """
    Show a Yes/No dialog on macOS using a tkinter dialog.

    Args:
        question: The question to ask the user
        title: Dialog window title

    Returns:
        - True: User clicked 'Yes'
        - False: User clicked 'No'
        - None: User clicked 'Stop' or cancelled
    """
    clicked = _show_tk_dialog(
        question,
        buttons=["Stop", "No", "Yes"],
        default_button="Yes",
        title=title,
    )
    if clicked == "Yes":
        return True
    if clicked == "No":
        return False
    return None


def ask_yes_no(question: str, title: str = "Confirmation") -> bool | None:
    """
    Ask a Yes/No question using a platform-specific dialog.

    Shows a dialog with Yes/No/Stop buttons (or equivalent).

    Args:
        question: The question to ask the user
        title: Dialog window title (default: 'Confirmation')

    Returns:
        - True: User answered 'Yes'
        - False: User answered 'No'
        - None: User cancelled or stopped

    Example:
        >>> if ask_yes_no('Did you exercise today?', 'Habit Check'):
        ...     print('Great job!')
    """
    platform_name = get_platform()
    if platform_name == "macos":
        return ask_yes_no_macos(question, title)

    # CLI fallback for other platforms
    print(f"\n{title}: {question}")
    while True:
        choice = input(" (y/n/s[top]): ").lower().strip()
        if choice.startswith("y"):
            return True
        if choice.startswith("n"):
            return False
        if choice.startswith("s"):
            return None
