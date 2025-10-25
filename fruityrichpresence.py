import time
import win32gui
import psutil
from pypresence import Presence

# ---- CONFIG ----
DISCORD_CLIENT_ID = "Discord Developer Portal Client ID You Created"
CHECK_INTERVAL = 0.1  # seconds

# ---- FUNCTIONS ----
def enum_windows_callback(hwnd, window_titles):
    title = win32gui.GetWindowText(hwnd)
    if "FL Studio" in title:
        window_titles.append(title)

def get_fl_windows():
    titles = []
    win32gui.EnumWindows(enum_windows_callback, titles)
    return titles

def extract_project_name(title):
    """Extracts the project name from an FL Studio window title."""
    title = title.strip()

    # Ignore main program windows like "FL Studio 10"
    if title.startswith("FL Studio"):
        return None

    # Projects look like "MySong - FL Studio 10"
    if " - FL Studio" in title:
        return title.split(" - FL Studio")[0].strip()

    return None


def is_flstudio_running():
    """Detect if any FL Studio window is open, regardless of process name."""
    def callback(hwnd, result):
        title = win32gui.GetWindowText(hwnd)
        if "FL Studio" in title:
            result.append(hwnd)
    hwnds = []
    win32gui.EnumWindows(callback, hwnds)
    return len(hwnds) > 0


def format_project_list(projects):
    if not projects:
        return "No projects open"
    if len(projects) == 1:
        return projects[0]
    return ", ".join(projects[:-1]) + " and " + projects[-1]

def get_focused_project():
    hwnd = win32gui.GetForegroundWindow()
    title = win32gui.GetWindowText(hwnd)
    if "FL Studio" in title:
        return extract_project_name(title)
    return None

# ---- MAIN ----
rpc = Presence(DISCORD_CLIENT_ID)
rpc.connect()

fl_running = False
cached_projects = set()
last_focus = None

print("Listening for FL Studio projects and focus changes...")

while True:
    time.sleep(CHECK_INTERVAL)

    running = is_flstudio_running()
    if not running:
        if fl_running:
            print("FL Studio closed — clearing presence.")
            rpc.clear()
            cached_projects.clear()
            fl_running = False
        continue

    fl_running = True
    windows = get_fl_windows()
    projects = []

    for title in windows:
        project = extract_project_name(title)
        if project:
            projects.append(project)

    projects = list(dict.fromkeys(projects))  # remove duplicates
    focused = get_focused_project()

    # Build display text
    if projects:
        project_text = format_project_list(projects)
        focus_text = f" (Tab: {focused})" if focused else ""
        combined_text = f"Projects: {project_text}{focus_text}"

        # --- NEW: detect and format FL Studio version numbers ---
        version_numbers = []
        for title in windows:
            # Extract version numbers from things like "MySong - FL Studio 12" or "FL Studio 20"
            if "FL Studio" in title:
                parts = title.split("FL Studio")
                if len(parts) > 1:
                    after = parts[1].strip()
                    num = ''.join(ch for ch in after if ch.isdigit())
                    if num:
                        version_numbers.append(int(num))

        # Remove duplicates and sort
        version_numbers = sorted(set(version_numbers))

        # Format versions for display
        if len(version_numbers) == 0:
            version_text = "FL Studio"
        elif len(version_numbers) == 1:
            version_text = f"FL Studio {version_numbers[0]}"
        elif len(version_numbers) == 2:
            version_text = f"FL Studio {version_numbers[0]} and {version_numbers[1]}"
        else:
            version_text = (
                "FL Studio " +
                ", ".join(str(v) for v in version_numbers[:-1]) +
                f", and {version_numbers[-1]}"
            )

        # Update Discord presence
        if set(projects) != cached_projects or focused != last_focus:
            cached_projects = set(projects)
            last_focus = focused
            print(combined_text)
            rpc.update(
                state=combined_text,
                details="Using " + version_text,
                large_image="flstudio10",
                large_text="Using " + version_text,  # <-- updated
                start=time.time()
            )
    else:
        print("No projects detected — clearing presence.")
        rpc.clear()
