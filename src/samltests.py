import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def main():
    # Initialize WebDriver
    driver_path = os.getenv("CHROMEDRIVER_PATH", "c:/webdrivers/chromedriver.exe")
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service)
    logging.info("WebDriver initialized successfully.")

    username = os.getenv("AAP_USERNAME")
    password = os.getenv("AAP_PASSWORD")

    if not username or not password:
        logging.error("Environment variables AAP_USERNAME or AAP_PASSWORD are not set.")
        return

    # Navigate to the login page
    url = "https://rhcpap-d.<your-domain>.net/#/login"
    driver.get(url)
    driver.set_window_size(1920, 1080)
    logging.info(f"Navigated to {url}.")

    wait = WebDriverWait(driver, 10)
    try:
        username_field = wait.until(EC.presence_of_element_located((By.ID, "pf-login-username-id")))
        username_field.clear()
        username_field.send_keys(username)
        logging.info("Username entered.")

        password_field = driver.find_element(By.ID, "pf-login-password-id")
        password_field.clear()
        password_field.send_keys(password)
        logging.info("Password entered.")

        login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Log In')]")
        login_button.click()
        logging.info("Login button clicked.")
    except TimeoutException:
        logging.error("Login elements not found. Exiting.")
        driver.quit()
        return

    # Navigate to SAML Settings and take screenshot
    try:
        settings_link = wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Settings")))
        settings_link.click()
        logging.info("Settings link clicked.")

        saml_settings_link = wait.until(EC.presence_of_element_located((By.LINK_TEXT, "SAML settings")))
        saml_settings_link.click()
        logging.info("SAML Settings link clicked.")

        edit_buttons = wait.until(EC.presence_of_all_elements_located((By.LINK_TEXT, "Edit")))
        if not edit_buttons:
            logging.info("No 'Edit' buttons found on the page.")
            driver.quit()
            return

        # Click the first "Edit" button and wait for the editor to load
        edit_buttons[0].click()
        logging.info("Clicked on the first 'Edit' button.")
        wait.until(EC.visibility_of_element_located((By.XPATH, "//div[@id='SOCIAL_AUTH_SAML_TEAM_ATTR-field']//div[contains(@class, 'monaco-editor')]")))
        logging.info("SAML editor loaded.")

        # Take screenshot
        screenshot_path = "saml_team_attribute_mapping.png"
        driver.save_screenshot(screenshot_path)
        logging.info(f"Screenshot saved at: {screenshot_path}")
    except TimeoutException:
        logging.error("Could not navigate to SAML settings or find editor. Exiting.")
    except NoSuchElementException as e:
        logging.error(f"Element not found: {e}. Exiting.")
    finally:
        driver.quit()
        logging.info("WebDriver closed.")

if __name__ == "__main__":
    main()