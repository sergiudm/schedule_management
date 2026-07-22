
---
sidebar_position: 1
---

# macOS Guide

Comprehensive guide for setting up and using Schedule Management on macOS.

## Installation

### Prerequisites
- macOS 10.14 (Mojave) or later
- Python 3.12 or higher
- Administrator privileges for system service setup

### Using the Installation Script

The easiest way to install on macOS:

```bash
# Clone the repository
git clone https://github.com/sergiudm/schedule_management.git
cd schedule_management

# Run the installation script
./install.sh
```

The script will:
1. Install Python dependencies
2. Create the application directory (`~/schedule_management/`)
3. Set up configuration files
4. Install the launchd service for auto-start
5. Configure the CLI tool

### Manual Installation

If you prefer manual control:

```bash
# Install Python package
pip install schedule-management

# Create directories
mkdir -p ~/schedule_management/config/user_config_0

# Copy configuration templates
cp config/settings_template.toml ~/schedule_management/config/user_config_0/settings.toml
cp config/week_schedule_template.toml ~/schedule_management/config/user_config_0/odd_weeks.toml
cp config/week_schedule_template.toml ~/schedule_management/config/user_config_0/even_weeks.toml

# Set up shell profile
echo 'export PATH="$HOME/schedule_management:$PATH"' >> ~/.zshrc
echo 'export REMINDER_CONFIG_DIR="$HOME/schedule_management/config"' >> ~/.zshrc
echo 'alias rmd="$HOME/schedule_management/rmd"' >> ~/.zshrc

# Reload shell
source ~/.zshrc
```

## System Service Setup

### LaunchAgent Configuration

The installation creates a LaunchAgent that runs the reminder service automatically:

**Location**: `~/Library/LaunchAgents/com.sergiudm.schedule_management.plist`

**Contents**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.sergiudm.schedule_management</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/YOUR_USERNAME/schedule_management/reminder_macos.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/YOUR_USERNAME/schedule_management/logs/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/YOUR_USERNAME/schedule_management/logs/stderr.log</string>
</dict>
</plist>
```

### Managing the Service

```bash
# Load the service (start automatically)
launchctl load ~/Library/LaunchAgents/com.sergiudm.schedule_management.plist

# Unload the service (stop automatically)
launchctl unload ~/Library/LaunchAgents/com.sergiudm.schedule_management.plist

# Check if service is running
launchctl list | grep schedule

# View service logs
tail -f ~/schedule_management/logs/stdout.log
tail -f ~/schedule_management/logs/stderr.log
```

## Daily Command Center App

Schedule Everything also ships with an optional Tauri 2 macOS app. The app is
designed for day-to-day operations: it shows the current/next event, today's
timeline, tasks, deadlines, habits, quick entry forms, and a preview/accept
flow for `rmd sync`.

It does not replace the CLI setup flow. Run `rmd setup` first so the local
config exists, then launch the app from source:

```bash
npm install
npm run tauri:dev
```

Build standalone app bundles with:

```bash
npm run tauri:build
```

The build includes a PyInstaller sidecar for the desktop JSON bridge and writes
the packaged app and DMG under `src-tauri/target/release/bundle/`.

## macOS Übersicht Desktop Widget

Schedule Everything includes an interactive desktop widget for [Übersicht](https://tracesof.net/uebersicht/) (`rmd-tasks.widget`), allowing you to view and manage your active tasks directly on your macOS desktop background.

### Overview & Capabilities

The widget renders `rmd ls` task items on the desktop wallpaper in real-time, matching category themes and priority colors.

### Interactive Task Deletion

Tasks displayed on the Übersicht desktop widget can be removed directly via GUI interaction with a two-step inline confirmation workflow:

1. **Initiate Deletion (`[✕]`)**: Each task item rendered on the widget includes an inline `[✕]` delete button. Clicking `[✕]` transitions the button state to `[Confirm?]` with a prominent red highlight.
2. **Two-Step Inline Confirmation**:
   - **Click 1 (`[✕]` -> `[Confirm?]`)**: Activates a 3-second confirmation window.
   - **Click 2 (`[Confirm?]` -> `...`)**: Executes `rmd rm <id>` asynchronously via Übersicht's execution bridge and immediately re-renders the updated task list on completion.
   - **Timeout Cancellation**: If `[Confirm?]` is not clicked within 3 seconds, the action times out and the button automatically resets back to `[✕]`.

### Installation & Maintenance

- **Automated Installer**: Running `./install.sh` on macOS interactively prompts to set up the Übersicht widget under `~/Library/Application Support/Übersicht/widgets/rmd-tasks.widget`.
- **Python Module**:
  ```python
  from schedule_management.desktop_widget import install_widget, uninstall_widget

  # Install widget template with configured rmd binary path
  install_widget()

  # Uninstall widget
  uninstall_widget()
  ```
- **Configuration (`settings.toml`)**:
  ```toml
  [desktop_widget]
  enabled = true          # Enable Übersicht desktop widget
  refresh_frequency = 30  # Widget refresh interval in seconds
  ```

## macOS-Specific Configuration

### Sound Files

macOS includes many built-in system sounds:

```toml
[settings]
# Popular system sounds
sound_file = "/System/Library/Sounds/Ping.aiff"
sound_file = "/System/Library/Sounds/Glass.aiff"
sound_file = "/System/Library/Sounds/Hero.aiff"
sound_file = "/System/Library/Sounds/Pop.aiff"
sound_file = "/System/Library/Sounds/Basso.aiff"
sound_file = "/System/Library/Sounds/Funk.aiff"
sound_file = "/System/Library/Sounds/Morse.aiff"
sound_file = "/System/Library/Sounds/Tink.aiff"

# Custom sound files
sound_file = "/Users/yourname/Music/notification.wav"
```

### Notification Settings

Schedule Management uses macOS native notifications. Configure notification settings:

1. **System Preferences** → **Notifications & Focus**
2. Find **Python** or **Terminal** in the app list
3. Configure:
   - Alert style: **Alerts** (for persistent notifications)
   - Allow notifications: **On**
   - Sounds: **On**
   - Badges: **On**

### Security & Privacy

Grant necessary permissions:

1. **System Preferences** → **Security & Privacy** → **Privacy**
2. **Accessibility**: Add Terminal/iTerm if needed
3. **Automation**: Allow Python to control System Events

## Troubleshooting macOS Issues

### Service Won't Start

```bash
# Check service
