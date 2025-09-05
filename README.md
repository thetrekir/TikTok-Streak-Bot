# TikTok Streak Bot

This bot designed to solve one specific, annoying problem: **maintaining TikTok streaks.**

Manually sending a message every day to keep a streak alive is a waste of mental energy. You forget, the streak dies, it's a chore. This script automates that chore.

### How It's Built to Not Fail

I built this thing to be solid because I never want to think about streaks again.

*   **No Lazy Timers:** It doesn't use `sleep(86400)` loop. It runs on a schedule.
*   **No Zombie Processes:** This system **guarantees** the browser is terminated and all temporary data is removed after every run, success or fail. No memory leaks, no disk space creep.
*   **No Blindness:** Bot keeps a detailed `log file` of every major action, warning, and critical error.
*   **Smart Configuration:** All needed variables are in `config.json`. The XPaths are hardcoded in the script. TikTok's frontend team is lazy. They haven't changed the core message UI in ages. If they ever do, you'll update a few variables at the top of the script. If I see it, I'll fix it and commit it.

### Installation

You need Python 3.

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/thetrekir/tiktok-streak-bot.git
    cd tiktok-streak-bot
    ```

2.  **Install Dependencies:** 
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

1.  **Test Run:**
    Set `"TEST_MODE": true` in the config and run `python main.py`. Check the console and the log file to see if it worked.

2.  **Deploy:**
    Set `"TEST_MODE": false` in the config. For a silent background process on Windows, run it with `pythonw.exe`:
    ```bash
    pythonw.exe main.py
    ```
    
    **For to open automatically after the system reboots, set this up as a Scheduled Task in Windows to run at logon.(I use this)**

### Troubleshooting

#### Error on Raspberry Pi / ARM64 Systems (`Exec format error`)

This bot is built for standard x86 systems. If you run it on an ARM machine like a Raspberry Pi, it will fail with an `Exec format error`.

**The Problem:** The automatic driver downloader (`webdriver-manager`) is can't fetch the correct `chromedriver` for ARM CPUs. It downloads the x86 version, which can't run.

**The Solution:** The script will now detect this and exit. To make it work, you must manually override the driver.

1.  **Use Firefox:** This is the most simple way. Install Firefox (`sudo apt-get install firefox-esr`), then modify `main.py` to use `webdriver.Firefox()` instead of `webdriver.Chrome()`. You'll need to adjust the `Service` object for geckodriver.

2.  **Manual Chrome Driver:** If you want on using Chrome, find and download a compatible ARM64 `chromedriver` binary yourself. Then, in `main.py`, find this line:
    `service = Service(ChromeDriverManager().install())`
    ...and replace it with a direct path:
    `service = Service(executable_path="/path/to/your/arm_chromedriver")`

### Is It Reliable? (Real-World Data)

A 100% success rate is a fantasy. Things break. Here's the data from about 90 days of it running live:

*   **Total Operations (Bot's Responsibility):** 80
*   **Successful Operations:** 76
*   **Operational Success Rate: 95%**

The 4 times it failed, it wasn't a bug in my code. It was TikTok being flaky.

* **June 4, 5, 23:** The UI glitched out. Clicks didn't register or it couldn't find the user in the list.

* **June 15:** The connection timed out waiting for the server to respond.

**The takeaway:** The bot's logic is solid. It works consistently, and the rare failures are due to the Tiktok.
