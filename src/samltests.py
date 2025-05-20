import os
import time
import json
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def main(org_name):
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
        return

    # Navigate to SAML Settings
    try:
        navigate_to_saml_settings(driver, wait, org_name)
    except TimeoutException:
        logging.error("Could not navigate to SAML settings. Exiting.")
    except NoSuchElementException as e:
        logging.error(f"Element not found: {e}. Exiting.")
    finally:
        driver.quit()
        logging.info("WebDriver closed.")

def navigate_to_saml_settings(driver, wait, org_name):
    """Navigates to SAML settings and searches for the organization."""
    settings_link = wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Settings")))
    settings_link.click()
    logging.info("Settings link clicked.")

    saml_settings_link = wait.until(EC.presence_of_element_located((By.LINK_TEXT, "SAML settings")))
    saml_settings_link.click()
    logging.info("SAML Settings link clicked.")

    find_and_screenshot_org(driver, wait, org_name)

def find_and_screenshot_org(driver, wait, org_name):
    """Search for the organization in the SAML attribute mapping and take a screenshot if found."""
    try:
        edit_buttons = driver.find_elements(By.LINK_TEXT, "Edit")
        if not edit_buttons:
            logging.info("No 'Edit' buttons found on the page.")
            return

        for button in edit_buttons:
            button.click()
            logging.info("Clicked on an 'Edit' button.")

            try:
                editor_container = wait.until(EC.presence_of_element_located(
                    (By.XPATH, "//div[@id='SOCIAL_AUTH_SAML_TEAM_ATTR-field']//textarea | //div[@id='SOCIAL_AUTH_SAML_TEAM_ATTR-field']//div[contains(@class, 'monaco-editor')]")
                ))
                logging.info("SAML editor loaded.")

                saml_team_attribute = scroll_and_get_editor_content(driver, editor_container)

                # Debug the retrieved content
                if not saml_team_attribute:
                    logging.error("Retrieved content is empty. Cannot parse JSON.")
                    return

                # Parse the JSON content
                try:
                    saml_data = json.loads(saml_team_attribute)
                    logging.info("SAML JSON successfully parsed.")

                    team_org_map = saml_data.get("team_org_map", [])
                    for entry in team_org_map:
                        if entry.get("organization") == org_name:
                            screenshot_path = f"{org_name}_saml_attribute_mapping.png"
                            driver.save_screenshot(screenshot_path)
                            logging.info(f"Organization '{org_name}' found. Screenshot saved at: {screenshot_path}")
                            return
                except json.JSONDecodeError as e:
                    logging.error(f"Failed to decode JSON. Content: {saml_team_attribute[:100]}... Error: {e}")
                    return
            except TimeoutException:
                logging.warning("SAML editor not found or failed to load within the timeout.")
            except NoSuchElementException as e:
                logging.warning(f"Error locating SAML attribute mapping editor: {e}")
            finally:
                driver.back()
                time.sleep(2)

        logging.info(f"Organization '{org_name}' not found in the SAML attribute mapping.")
    except Exception as e:
        logging.error(f"An error occurred while searching for the organization: {e}")

def scroll_and_get_editor_content(driver, editor_container):
    """Retrieve the JSON content from the Monaco editor."""
    try:
        editor_script = """
            const container = arguments[0];
            // Try to find a textarea first
            const textarea = container.querySelector('textarea');
            if (textarea) {
                return textarea.value;
            }
            // If no textarea, assume it's a Monaco editor and extract content from the model
            const monacoEditor = container.querySelector('.monaco-editor');
            if (monacoEditor) {
                const editorInstance = monaco.editor.getEditors().find(editor => editor.getContainerDomNode() === monacoEditor);
                if (editorInstance) {
                    return editorInstance.getValue();
                }
            }
            // Fallback to textContent if Monaco editor API is unavailable
            return container.textContent || '';
        """
        saml_content = driver.execute_script(editor_script, editor_container)
        logging.info(f"Retrieved content from the editor: {saml_content[:100]}...")
        return saml_content.strip()  # Remove leading/trailing whitespace
    except Exception as e:
        logging.error(f"Failed to retrieve content from the editor: {e}")
        return ""

if __name__ == "__main__":
    org_name = input("Enter the organization name to search: ")
    main(org_name)