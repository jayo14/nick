import re
import time
import urllib.parse
import json
from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def decode_moodle_ajax(url):
    """Decodes Moodle AJAX arguments to see the actual function names."""
    try:
        parsed_url = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed_url.query)
        if 'args' in params:
            decoded_args = urllib.parse.unquote(params['args'][0])
            return f" [Moodle Logic: {decoded_args[:100]}...]"
    except:
        pass
    return ""

def discover_with_selenium(target_url):
    print(f"[*] Launching automated discovery for: {target_url}")

    chrome_options = Options()
    # chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--disable-blink-features=AutomationControlled") 
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), 
        options=chrome_options
    )
    
    found_endpoints = set()

    try:
        # --- PHASE 1: Initial Load ---
        driver.get(target_url)
        time.sleep(4)

        # --- PHASE 2: Form Interaction (Automated Typing/Submit) ---
        print("[*] Attempting to trigger POST endpoints via form interaction...")
        try:
            # Look for common Moodle forgot password fields
            input_box = None
            for selector in ["#id_email", "#id_username", "input[name='email']", "input[name='username']"]:
                try:
                    input_box = driver.find_element(By.CSS_SELECTOR, selector)
                    if input_box: break
                except: continue
            
            if input_box:
                input_box.send_keys("discovery_test@kwasu.edu.ng")
                # Find and click the submit button
                submit_btn = driver.find_element(By.CSS_SELECTOR, "input[type='submit'], button[type='submit']")
                submit_btn.click()
                print("[+] Form submitted. Capturing redirection traffic...")
                time.sleep(5) # Wait for redirect/POST response
        except Exception as e:
            print(f"[!] Interaction failed (might not be a form here): {e}")

        # --- PHASE 3: Extraction ---
        # 1. DOM Extraction
        elements = driver.find_elements(By.XPATH, "//*[@src or @href or @action]")
        for el in elements:
            for attr in ['src', 'href', 'action']:
                try:
                    val = el.get_attribute(attr)
                    if val: found_endpoints.add(val)
                except: continue

        # 2. Regex Search
        patterns = [
            r'https?://[\w\.-]+(?:/api/[\w/\.-]+)?',
            r'/(?:api|v\d|graphql|json|webservice)/[\w\.-/]+'
        ]
        for pattern in patterns:
            matches = re.findall(pattern, driver.page_source)
            found_endpoints.update(matches)

        # 3. Capture Background "Wire" Traffic
        print("\n[+] Traffic Captured (including AJAX & POST):")
        for request in driver.requests:
            if request.response:
                url = request.url
                if any(x in url.lower() for x in ["php", "json", "service", "api", "webservice"]):
                    moodle_info = decode_moodle_ajax(url)
                    print(f"[{request.method}] {request.response.status_code} | {url}{moodle_info}")
                    found_endpoints.add(url)

        return found_endpoints

    except Exception as e:
        print(f"[!] Error: {e}")
        return []
    finally:
        driver.quit()

# Usage
target = "https://lms.kwasu.edu.ng/login/forgot_password.php"
results = discover_with_selenium(target)

print("\n--- Final Filtered Results ---")
for r in sorted(results):
    if "kwasu.edu.ng" in r or r.startswith("/"):
        # Clean up session keys for cleaner output if desired
        print(r)