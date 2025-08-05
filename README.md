# TikTok Streak Bot

This isn't an "auto-messenger." It's a fire-and-forget bot designed to solve one specific, annoying problem: **maintaining TikTok streaks.**

Manually sending a message every day to keep a streak alive is a waste of mental energy. You forget, the streak dies, it's a chore. This script automates that chore out of existence. You set it up once, and you never think about it again.

### How It's Built to Not Fail

This system was designed for one thing: **unattended reliability**. It expects things to break, because over weeks and months, they will. The enemy isn't TikTok; it's time, random glitches, and system instability.

Here’s how it survives:

*   **No Sloppy Timers:** It doesn't use a lazy `sleep(86400)` loop. It runs on a precise schedule, waking up at the exact minute you specify each day.
*   **No Zombie Processes:** A script that crashes can leave behind zombie browsers and locked temp files. This system **guarantees** the browser is terminated and all temporary data is vaporized after every run, success or fail. No memory leaks, no disk space creep.
*   **No Blindness:** Headless bots are black boxes. This one keeps a detailed `log file` of every major action, warning, and critical error. It’s the flight recorder for your bot.
*   **Smart Configuration:** All user-facing variables are in `config.json`. You never need to touch the code for day-to-day changes. The UI selectors (XPaths) are hardcoded in the script. This is a calculated risk based on one fact: TikTok's frontend team is lazy. They haven't changed the core message UI in ages. If they ever do, you'll update a few variables at the top of the script. Until then, this is the most direct approach.

### Installation

You need Python 3. That's it.

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/thetrekir/tiktok-streak-bot.git
    cd tiktok-streak-bot
    ```

2.  **Install Dependencies:**
    This installs Selenium and everything else.
    ```bash
    pip install -r requirements.txt
    ```

3.  **Get Your Cookies:**
    The bot uses cookies to log in. No password needed.
    *   Log in to TikTok in your browser.
    *   Use an extension like [Cookie-Editor](https://cookie-editor.com/) to export your cookies for the `tiktok.com` domain.
    *   Save the exported JSON data into a file named `cookies.json` in the same directory.

4.  **Configure It:**
    The first time you run the script, it will create a `config.json` file. Open it and set it up.

### Configuration (`config.json`)

This file controls the bot.

```json
{
  "TEST_MODE": false,
  "TARGET_USERS": ["username1", "username2"],
  "MESSAGE_TO_SEND": ".",
  "TARGET_SEND_TIME_HM": [0, 2],
  "COOKIES_FILE": "cookies.json",
  "LOG_FILENAME": "tiktok_bot.txt",
  "HEADLESS_MODE": true
}
```

*   `TEST_MODE`: `true` runs it once, now. `false` uses the daily schedule.
*   `TARGET_USERS`: List of usernames to send the message to.
*   `MESSAGE_TO_SEND`: The message. `.` is enough.
*   `TARGET_SEND_TIME_HM`: `[Hour, Minute]` in 24-hour format. `[0, 2]` means 00:02 AM.
*   `COOKIES_FILE`: Name of your cookies file.
*   `LOG_FILENAME`: Name of the log file.
*   `HEADLESS_MODE`: `true` runs it invisibly. `false` shows the browser window.

### Usage

Set it and forget it.

1.  **Test Run:**
    Set `"TEST_MODE": true` in the config and run `python main.py`. Check the console and the log file to see if it worked.

2.  **Deploy:**
    Set `"TEST_MODE": false` in the config. For a silent background process on Windows, run it with `pythonw.exe`:
    ```bash
    pythonw.exe main.py
    ```
    The script is now running in the background. To stop it, you'll need to kill the `pythonw.exe` process in Task Manager.

    **For true persistence across system reboots, set this up as a Scheduled Task in Windows to run at logon. That is the ultimate fire-and-forget setup.**

### Is It Reliable? (Real-World Data)

This isn't a theoretical toy. It's been running autonomously in the wild since early May 2025.

Let's be blunt. Here's the operational data from a ~90-day period:

*   **Total Operations (Bot's Responsibility):** 80
*   **Successful Operations:** 76
*   **Operational Success Rate: 95%**

A 100% success rate in this environment is a fantasy. The 4 failures weren't bugs in the code. They were the environment fighting back:

*   **UI/Platform Instability:** On three separate days (June 4, June 5, June 23), operations failed due to the platform's environment. These issues included intercepted clicks, suggesting a temporary UI change, and the inability to locate target users in the conversation list.
*   **Network/Server Timeouts:** On one occasion (June 15), the operation failed because the connection to the servers timed out while waiting for the conversation list to load. This is an external network issue, not a flaw in the bot.

**The takeaway:** The bot's logic is solid. It works consistently, and the rare failures are due to the unpredictable nature of the platform it operates on. It's built to survive these hiccups and continue its mission the next day.

**Operational Note:** It's also important to mention that the system was intentionally shut down for a 10-day period for maintenance. This planned downtime is not factored into the operational success rate, as it was not a system failure.
