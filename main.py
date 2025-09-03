import time
import json
import logging
import random
import sys
import os
import shutil
import tempfile
import platform
from datetime import datetime, time as dt_time, date, timedelta
from contextlib import contextmanager

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException, ElementNotInteractableException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

os.environ['WDM_LOG'] = '0'
from webdriver_manager.chrome import ChromeDriverManager


CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
  "TEST_MODE": False,
  "TARGET_USERS": ["kullanici1", "kullanici2"],
  "MESSAGE_TO_SEND": ".",
  "TARGET_SEND_TIME_HM": [0, 2],
  "COOKIES_FILE": "cookies.json",
  "LOG_FILENAME": "tiktok_bot.txt",
  "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
  "TIKTOK_MESSAGES_URL": "https://www.tiktok.com/messages?lang=tr-TR",
  "HEADLESS_MODE": True
}

def load_or_create_config(filename):
    if not os.path.exists(filename):
        logging.warning(f"Configuration file '{filename}' not found. Creating it with default values.")
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
            logging.info(f"Default configuration file '{filename}' created successfully.")
            return DEFAULT_CONFIG
        except IOError as e:
            logging.error(f"ERROR: Could not create configuration file '{filename}': {e}")
            return None
        except Exception as e:
            logging.error(f"ERROR: An unexpected error occurred while creating config file '{filename}': {e}")
            return None
    else:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            logging.info(f"Configuration loaded successfully from existing '{filename}'.")
            return config_data
        except json.JSONDecodeError as e:
            logging.error(f"ERROR: Configuration file '{filename}' contains invalid JSON: {e}")
            return None
        except Exception as e:
            logging.error(f"ERROR: An unexpected error occurred while loading config file '{filename}': {e}")
            return None

def terminate_lingering_processes():
    logging.info("Searching for and terminating any lingering chrome/chromedriver processes...")
    try:
        os.system("taskkill /F /IM chromedriver.exe /T > NUL 2>&1")
        os.system("taskkill /F /IM chrome.exe /T > NUL 2>&1")
        logging.info("Process termination commands executed.")
    except Exception as e:
        logging.error(f"An error occurred during process termination: {e}")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.StreamHandler()])

config = load_or_create_config(CONFIG_FILE)
if config is None:
    logging.critical("Exiting due to configuration file error (loading or creation failed).")
    sys.exit(1)

TEST_MODE = config.get('TEST_MODE', DEFAULT_CONFIG['TEST_MODE'])
TARGET_USERS = config.get('TARGET_USERS', DEFAULT_CONFIG['TARGET_USERS'])
MESSAGE_TO_SEND = config.get('MESSAGE_TO_SEND', DEFAULT_CONFIG['MESSAGE_TO_SEND'])
time_hm = config.get('TARGET_SEND_TIME_HM', DEFAULT_CONFIG['TARGET_SEND_TIME_HM'])
COOKIES_FILE = config.get('COOKIES_FILE', DEFAULT_CONFIG['COOKIES_FILE'])
LOG_FILENAME = config.get('LOG_FILENAME', DEFAULT_CONFIG['LOG_FILENAME'])
USER_AGENT = config.get('USER_AGENT', DEFAULT_CONFIG['USER_AGENT'])
TIKTOK_MESSAGES_URL = config.get('TIKTOK_MESSAGES_URL', DEFAULT_CONFIG['TIKTOK_MESSAGES_URL'])
HEADLESS_MODE = config.get('HEADLESS_MODE', DEFAULT_CONFIG['HEADLESS_MODE'])

try:
    if isinstance(time_hm, list) and len(time_hm) == 2:
        TARGET_SEND_TIME = dt_time(int(time_hm[0]), int(time_hm[1]))
    else:
        raise ValueError("TARGET_SEND_TIME_HM must be a list of [hour, minute]")
except (ValueError, TypeError) as e:
    logging.error(f"Invalid TARGET_SEND_TIME_HM format in config: {time_hm}. Error: {e}. Using default {DEFAULT_CONFIG['TARGET_SEND_TIME_HM']}.")
    TARGET_SEND_TIME = dt_time(DEFAULT_CONFIG['TARGET_SEND_TIME_HM'][0], DEFAULT_CONFIG['TARGET_SEND_TIME_HM'][1])

if not TARGET_USERS:
    logging.warning("Warning: TARGET_USERS list is empty in the configuration. The bot will run but won't send messages.")

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILENAME, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logging.info("--- Bot Started ---")
logging.info(f"Using configuration from '{CONFIG_FILE}'. TEST_MODE: {TEST_MODE}, Target Time: {TARGET_SEND_TIME.strftime('%H:%M')}")

MESSAGE_LIST_CONTAINER_XPATH = '//*[@id="app"]/div[2]/div[1]/div/div[4]/div/div/div[2]'
CONVERSATION_ITEM_XPATH = "//div[@data-e2e='chat-list-item']"
NICKNAME_CLASS_PARTIAL = "PInfoNickname"
NICKNAME_XPATH_INSIDE_ITEM = f".//p[contains(@class, '{NICKNAME_CLASS_PARTIAL}')]"
CLICK_TARGET_XPATH = '//*[@id="main-content-messages"]/div/div[3]/div[4]/div'
WRITE_TARGET_XPATH = '//*[@id="main-content-messages"]/div/div[3]/div[4]/div/div[1]/div/div[2]/div[2]/div/div/div/div'
TOAST_XPATH = "//li[@data-sonner-toast]"

def load_cookies(driver, cookie_file):
    logging.info(f"Loading cookies from '{cookie_file}'...")
    cookies_added_count = 0
    cookies_failed_count = 0
    try:
        with open(cookie_file, 'r') as f:
            cookies = json.load(f)
        logging.info(f"Read {len(cookies)} cookies from file.")

        driver.get("https://www.tiktok.com/explore")
        logging.info(f"Navigated to main domain: {driver.current_url}. Waiting before adding cookies...")
        time.sleep(random.uniform(3, 5))
        logging.info(f"Starting to add cookies (Browser at {driver.current_url})")

        for i, cookie in enumerate(cookies):
            cookie_to_add = {}
            try:
                cookie_to_add['name'] = cookie['name']
                cookie_to_add['value'] = cookie['value']
                if 'path' in cookie: cookie_to_add['path'] = cookie['path']
                if 'domain' in cookie: cookie_to_add['domain'] = cookie['domain']
                if 'secure' in cookie: cookie_to_add['secure'] = cookie['secure']
                if 'httpOnly' in cookie: cookie_to_add['httpOnly'] = cookie['httpOnly']

                if 'expirationDate' in cookie and cookie['expirationDate']:
                    try:
                        expiry_timestamp = int(float(cookie['expirationDate']))
                        cookie_to_add['expiry'] = expiry_timestamp
                    except (ValueError, TypeError):
                        logging.debug(f"C#{i+1} ('{cookie.get('name')}') invalid expirationDate. Skipping expiry.")

                if 'sameSite' in cookie:
                    samesite_value = cookie['sameSite']
                    if samesite_value is None or isinstance(samesite_value, str) and samesite_value.lower() == 'no_restriction':
                         if cookie_to_add.get('secure'):
                             cookie_to_add['sameSite'] = 'None'
                         else:
                             logging.debug(f"C#{i+1} ('{cookie.get('name')}') SameSite=None/null but not secure. Skipping SS.")
                    elif isinstance(samesite_value, str) and samesite_value.lower() in ['lax', 'strict', 'none']:
                         cookie_to_add['sameSite'] = samesite_value.capitalize()
                    else:
                         logging.debug(f"C#{i+1} ('{cookie.get('name')}') unknown sameSite value. Skipping SS.")

                if 'domain' not in cookie_to_add or not cookie_to_add['domain']:
                     cookie_to_add['domain'] = ".tiktok.com"

                logging.debug(f"Attempting to add cookie #{i+1}: {cookie_to_add}")
                driver.add_cookie(cookie_to_add)
                cookies_added_count += 1

            except Exception as e:
                cookies_failed_count += 1
                logging.warning(f"Failed to add cookie C#{i+1} ('{cookie.get('name', 'N/A')}'). Error: {type(e).__name__}")
                logging.debug(f"Failed cookie details: {cookie_to_add}")

        if cookies_failed_count > 0:
            logging.warning(f"{cookies_failed_count} cookies failed to load.")
        if cookies_added_count > 0:
             logging.info(f"Successfully added {cookies_added_count} cookies.")
             return True
        else:
             logging.error("No cookies were added!")
             return False
    except FileNotFoundError:
        logging.error(f"Cookie file not found: {cookie_file}")
        return False
    except json.JSONDecodeError:
        logging.error(f"Cookie file is not valid JSON: {cookie_file}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error during cookie loading:")
        logging.exception(e)
        return False

def wait_for_element(driver, by, value, timeout=20):
    try:
        element_present = EC.presence_of_element_located((by, value))
        WebDriverWait(driver, timeout).until(element_present)
        logging.info(f"Element found: {by}={value}")
        return True
    except TimeoutException:
        logging.error(f"Timeout waiting for element: {by}={value} (in {timeout}s)")
        return False

def find_and_click_conversation(driver, username):
    logging.info(f"Searching for conversation with '{username}'...")
    try:
        logging.info(f"Waiting for conversation items (XPath: {CONVERSATION_ITEM_XPATH})")
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, CONVERSATION_ITEM_XPATH))
        )
        time.sleep(random.uniform(2, 4))

        conversation_items = driver.find_elements(By.XPATH, CONVERSATION_ITEM_XPATH)
        logging.info(f"Found {len(conversation_items)} conversation items using XPath: {CONVERSATION_ITEM_XPATH}")

        if not conversation_items:
            logging.warning("No conversation items found!")
            return False

        user_found_and_clicked = False
        for i, item in enumerate(conversation_items):
            try:
                nickname_element = item.find_element(By.XPATH, NICKNAME_XPATH_INSIDE_ITEM)
                nickname_text = nickname_element.text.strip()
                logging.debug(f"Item #{i+1}: Found nickname: '{nickname_text}'")

                if nickname_text.lower() == username.lower():
                    logging.info(f"Found '{username}' at item #{i+1}. Clicking...")
                    driver.execute_script("arguments[0].scrollIntoView(true);", item)
                    time.sleep(0.5)
                    item.click()
                    user_found_and_clicked = True
                    time.sleep(random.uniform(3, 5))
                    return True

            except NoSuchElementException:
                 logging.debug(f"Item #{i+1} does not contain nickname (XPath: {NICKNAME_XPATH_INSIDE_ITEM}).")
                 continue
            except StaleElementReferenceException:
                logging.warning(f"Stale element reference for item #{i+1}. Retrying search...")
                logging.warning("Skipping this stale item and continuing search.")
                continue
            except Exception as e:
                logging.error(f"Error processing conversation item #{i+1}: {e}")
                continue

        if not user_found_and_clicked:
            logging.warning(f"'{username}' not found in the {len(conversation_items)} items.")
            return False

    except TimeoutException:
        logging.error(f"Timeout waiting for conversation items (XPath: {CONVERSATION_ITEM_XPATH}).")
        return False
    except Exception as e:
        logging.error(f"Unexpected error searching/clicking conversation: {e}")
        return False
    return False

def send_message_in_open_chat(driver):
    logging.info("Attempting to send message in the open chat...")
    click_target = None
    write_target = None

    try:
        try:
            logging.debug("Waiting for potential toast notification to disappear...")
            WebDriverWait(driver, 7).until(EC.invisibility_of_element_located((By.XPATH, TOAST_XPATH)))
            logging.info("Toast notification (if any) disappeared.")
        except TimeoutException:
            logging.debug("Toast notification not found or did not disappear in time.")
        except Exception as e:
            logging.warning(f"Error waiting for toast: {e}")

        logging.info(f"Waiting for the click target area (XPath: {CLICK_TARGET_XPATH})")
        try:
            click_target = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, CLICK_TARGET_XPATH))
            )
            logging.info("Click target found and clickable.")
        except TimeoutException:
            logging.error(f"Could not find clickable target (XPath: {CLICK_TARGET_XPATH})!")
            return False

        logging.info("Clicking the target area...")
        try:
            driver.execute_script("arguments[0].scrollIntoView(true);", click_target)
            time.sleep(0.5)
            click_target.click()
            logging.info("Clicked target area.")
            time.sleep(random.uniform(1.5, 2.5))
        except Exception as click_err:
            logging.warning(f"Normal click failed ({type(click_err).__name__}). Trying JS click...")
            try:
                driver.execute_script("arguments[0].scrollIntoView(true);", click_target)
                time.sleep(0.3)
                driver.execute_script("arguments[0].click();", click_target)
                logging.info("Clicked via Javascript.")
                time.sleep(random.uniform(1.5, 2.5))
            except Exception as js_click_err:
                 logging.error(f"Javascript click also failed: {js_click_err}")
                 return False

        logging.info(f"Waiting for the write target area (XPath: {WRITE_TARGET_XPATH})...")
        try:
            write_target = WebDriverWait(driver, 15).until(
                EC.visibility_of_element_located((By.XPATH, WRITE_TARGET_XPATH))
            )
            logging.info("Found the write target area.")
            try:
                driver.execute_script("arguments[0].focus();", write_target)
                logging.info("Focused the write target area.")
                time.sleep(0.5)
            except Exception as focus_err:
                logging.warning(f"Could not focus write target area (may be okay): {focus_err}")

        except TimeoutException:
             logging.error(f"Could not find the write target area (XPath: {WRITE_TARGET_XPATH}) after clicking!")
             return False

        logging.info(f"Sending keys to write target: '{MESSAGE_TO_SEND}'")
        try:
             WebDriverWait(driver, 5).until(EC.element_to_be_clickable(write_target))
             write_target.send_keys(MESSAGE_TO_SEND)
             time.sleep(random.uniform(0.8, 1.5))
             write_target.send_keys(Keys.ENTER)
             logging.info("Message sent (Enter key pressed).")
             time.sleep(random.uniform(2, 4))
             return True
        except ElementNotInteractableException as send_keys_err:
             logging.warning(f"Normal send_keys failed ({type(send_keys_err).__name__}). Trying JS value set...")
             try:
                 driver.execute_script("arguments[0].textContent = arguments[1];", write_target, MESSAGE_TO_SEND)
                 time.sleep(random.uniform(0.5, 1.0))
                 write_target.send_keys(Keys.ENTER)
                 logging.info("Set value via JS and pressed Enter.")
                 time.sleep(random.uniform(2, 4))
                 return True
             except Exception as js_err:
                 logging.error(f"JS value set or subsequent Enter failed: {type(js_err).__name__} - {js_err}")
                 logging.exception("Traceback:")
                 return False
        except Exception as other_send_err:
            logging.error(f"Error during send_keys or Enter: {type(other_send_err).__name__} - {other_send_err}")
            logging.exception("Traceback:")
            return False

    except Exception as e:
        logging.error(f"General error in send_message_in_open_chat: {e}")
        logging.exception(e)
        return False

def handle_passkey_popup(driver):
    logging.info("Checking for the 'passkey' creation popup...")
    passkey_popup_button_xpath = "//div[@role='dialog']//button[contains(., 'Belki daha sonra')]"
    try:
        wait = WebDriverWait(driver, 15)
        maybe_later_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, passkey_popup_button_xpath))
        )
        logging.info("Passkey popup found. Clicking 'Maybe later'...")
        maybe_later_button.click()
        logging.info("Waiting for the passkey popup to disappear...")
        wait.until(
            EC.invisibility_of_element_located((By.XPATH, passkey_popup_button_xpath))
        )
        logging.info("Passkey popup dismissed successfully.")
    except TimeoutException:
        logging.info("Passkey popup did not appear or was already gone, continuing...")
    except Exception as e:
        logging.warning(f"An error occurred while handling the passkey popup: {e}")

@contextmanager
def is_arm_architecture():
    machine_arch = platform.machine().lower()
    return 'arm' in machine_arch or 'aarch64' in machine_arch

def managed_webdriver(headless, user_agent):
    terminate_lingering_processes()
    time.sleep(1)
    if is_arm_architecture():
        try:
            Service(executable_path=ChromeDriverManager().install())
        except Exception as e:
            if "Exec format error" in str(e) or is_arm_architecture():
                 logging.critical("ARM ARCHITECTURE DETECTED AND NO COMPATIBLE DRIVER FOUND.")
                 logging.critical("webdriver-manager cannot automatically download a driver for this system.")
                 logging.critical("See the 'Troubleshooting' section in README.md for manual solutions.")
                 sys.exit(1)

    user_data_dir = tempfile.mkdtemp()
    logging.info(f"Using temporary user data directory: {user_data_dir}")
    
    driver = None
    try:
        chrome_options = Options()
        if headless:
            logging.info("Running in HEADLESS mode.")
            chrome_options.add_argument("--headless=new")
        else:
            logging.info("Running in standard (non-headless) mode.")
        
        chrome_options.add_argument(f"user-agent={user_agent}")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--mute-audio")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        yield driver

    finally:
        logging.info("Entering cleanup phase...")
        if driver:
            try:
                logging.info("Attempting graceful shutdown with driver.quit().")
                driver.quit()
                time.sleep(2) 
            except Exception as e:
                logging.warning(f"Error during driver.quit() (might be already closed): {e}")
        
        terminate_lingering_processes()
        
        logging.info(f"Cleaning up temporary user data directory: {user_data_dir}")
        try:
            time.sleep(2)
            shutil.rmtree(user_data_dir, ignore_errors=True)
            logging.info(f"Successfully initiated cleanup for temp directory: {user_data_dir}")
        except Exception as e:
            logging.error(f"CRITICAL: Failed to remove temp directory {user_data_dir}. This may cause issues on next run. Error: {e}")

def run_bot():
    if TEST_MODE:
        logging.warning("--- TEST MODE (Instant Run) ACTIVE ---")
    else:
        logging.info("--- Normal Mode (Scheduled Run) Starting ---")

    try:
        with managed_webdriver(headless=HEADLESS_MODE, user_agent=USER_AGENT) as driver:
            logging.info("Browser opened and managed by context.")

            if not load_cookies(driver, COOKIES_FILE):
                raise Exception("Failed to load cookies, stopping bot run.")

            logging.info(f"Navigating to '{TIKTOK_MESSAGES_URL}'...")
            driver.get(TIKTOK_MESSAGES_URL)

            handle_passkey_popup(driver)

            logging.info(f"Waiting for message list container ({MESSAGE_LIST_CONTAINER_XPATH})...")
            if not wait_for_element(driver, By.XPATH, MESSAGE_LIST_CONTAINER_XPATH, timeout=35):
                logging.warning("Message list container not found. This might cause issues.")
            else:
                logging.info("Message list container loaded.")
            time.sleep(random.uniform(3, 6))

            users_to_message = TARGET_USERS
            if not users_to_message:
                logging.error("Target user list is empty. Nothing to do. Exiting run.")
                return

            success_count = 0
            logging.info(f"Will attempt to send messages to {len(users_to_message)} target users: {', '.join(users_to_message)}")

            for user in users_to_message:
                loggable_user = ''.join(c for c in user if c.isprintable())
                logging.info(f"--- Processing user: '{loggable_user}' ---")
                if find_and_click_conversation(driver, user):
                    if send_message_in_open_chat(driver):
                        success_count += 1
                        logging.info(f"Message successfully sent to '{loggable_user}'.")
                    else:
                        logging.warning(f"Opened chat for '{loggable_user}' but FAILED TO SEND a message.")
                else:
                    logging.warning(f"Could not find or click conversation for '{loggable_user}'.")

                if len(users_to_message) > 1 and user != users_to_message[-1]:
                    wait_time = random.uniform(5, 10)
                    logging.info(f"Waiting {wait_time:.1f} seconds before next user...")
                    time.sleep(wait_time)

            logging.info(f"Finished processing. {success_count}/{len(users_to_message)} messages successfully sent.")

    except Exception as e:
        logging.error("Critical error during bot execution:")
        logging.exception(e)

if __name__ == "__main__":
    if TEST_MODE:
        logging.info("Test mode enabled. Running bot immediately.")
        run_bot()
        logging.info("Test mode run finished.")
    else:
        last_run_date = None
        logging.info(f"Normal mode enabled. Scheduling for {TARGET_SEND_TIME.strftime('%H:%M')}. Starting loop...")

        while True:
            now = datetime.now()
            current_time = now.time()
            today = now.date()
            
            target_plus_one_minute = (datetime.combine(date.today(), TARGET_SEND_TIME) + timedelta(minutes=1)).time()

            time_in_range = TARGET_SEND_TIME <= current_time < target_plus_one_minute

            if time_in_range and today != last_run_date:
                logging.info(f"Target time reached ({current_time.strftime('%H:%M:%S')}). Running bot in normal mode...")
                try:
                    run_bot()
                except Exception as e:
                     logging.error(f"FATAL: An unhandled exception escaped from run_bot: {e}")
                finally:
                    last_run_date = today
                    logging.info(f"Normal mode run for {today} completed. Waiting until tomorrow {TARGET_SEND_TIME.strftime('%H:%M')}.")

            now = datetime.now()
            next_run_dt = datetime.combine(now.date(), TARGET_SEND_TIME)
            if now > next_run_dt:
                next_run_dt += timedelta(days=1)
            
            sleep_seconds = (next_run_dt - now).total_seconds()
            if sleep_seconds < 300:
                check_interval_seconds = 5
            else:
                check_interval_seconds = 60

            logging.debug(f"Next check in {check_interval_seconds} seconds. Next run target: {next_run_dt.strftime('%Y-%m-%d %H:%M:%S')}")
            time.sleep(check_interval_seconds)
