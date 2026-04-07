from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import re

def discover_with_selenium(target_url):
    print(f"[*] Launching controlled browser for: {target_url}")

    # Set up Chrome options
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # Uncomment to run without a window
    chrome_options.add_argument("--disable-blink-features=AutomationControlled") 
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    # Initialize the driver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    found_endpoints = set()

    try:
        driver.get(target_url)
        
        # Give the page 5 seconds to execute JavaScript and load background resources
        time.sleep(5)

        # 1. Extract endpoints from the DOM (Links, Forms, Scripts)
        elements = driver.find_elements("xpath", "//*[@src or @href or @action]")
        for el in elements:
            for attr in ['src', 'href', 'action']:
                val = el.get_attribute(attr)
                if val:
                    found_endpoints.add(val)

        # 2. Search for API/v1 patterns in the rendered HTML source
        patterns = [
            r'https?://[\w\.-]+(?:/api/[\w/\.-]+)?',
            r'/(?:api|v\d|graphql|json)/[\w\.-/]+'
        ]
        page_source = driver.page_source
        for pattern in patterns:
            matches = re.findall(pattern, page_source)
            found_endpoints.update(matches)

        print(f"[+] Extraction complete. Found {len(found_endpoints)} potential items.")
        return found_endpoints

    except Exception as e:
        print(f"[!] Selenium Error: {e}")
        return []
    finally:
        driver.quit()

# Usage
target = "https://lms.kwasu.edu.ng/login/forgot_password.php"
results = discover_with_selenium(target)

print("\n--- Discovered Endpoints ---")
for r in sorted(results):
    if "kwasu.edu.ng" in r or r.startswith("/"):
        print(r)