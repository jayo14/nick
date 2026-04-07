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
            # Return a cleaned up version of the JSON args
            return f" -> [Moodle Action: {decoded_args[:120]}]"
    except:
        pass
    return ""

def discover_with_selenium(target_url):
    print(f"[*] Launching Deep Discovery for: {target_url}")

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
        # --- PHASE 1: Initial Load & Header Capture ---
        driver.get(target_url)
        time.sleep(4)

        # --- PHASE 2: Automated Form Interaction ---
        print("[*] Interacting with form to trigger hidden POST logic...")
        try:
            # Smart selector for Moodle's reset fields
            selectors = ["#id_email", "#id_username", "input[name='email']", "input[name='username']"]
            input_box = None
            for selector in selectors:
                try:
                    input_box = driver.find_element(By.CSS_SELECTOR, selector)
                    if input_box: break
                except: continue
            
            if input_box:
                input_box.send_keys("discovery_test@kwasu.edu.ng")
                submit_btn = driver.find_element(By.CSS_SELECTOR, "input[type='submit'], button[type='submit']")
                submit_btn.click()
                print("[+] Interaction successful. Monitoring response...")
                time.sleep(5) 
        except Exception as e:
            print(f"[-] Interaction skipped: {e}")

        # --- PHASE 3: Deep Traffic Analysis ---
        print("\n" + "="*50)
        print("INTERCEPTED DATA FLOW")
        print("="*50)

        for request in driver.requests:
            if request.response:
                url = request.url
                # Focus only on target domain
                if "kwasu.edu.ng" in url.lower():
                    status = request.response.status_code
                    method = request.method
                    moodle_meta = decode_moodle_ajax(url)

                    print(f"[{method}] {status} | {url}{moodle_meta}")

                    # --- NEW: POST Payload Inspection ---
                    if method == "POST" and request.body:
                        try:
                            body = request.body.decode('utf-8', errors='ignore')
                            print(f"    └─ [PAYLOAD]: {body[:200]}")
                        except:
                            pass

                    # --- NEW: Header Security Check ---
                    if 'sesskey' in url:
                        found_endpoints.add(url)

        # --- PHASE 4: Scrape Rendered DOM & Regex ---
        page_source = driver.page_source
        
        # DOM Extraction
        elements = driver.find_elements(By.XPATH, "//*[@src or @href or @action]")
        for el in elements:
            for attr in ['src', 'href', 'action']:
                try:
                    val = el.get_attribute(attr)
                    if val: found_endpoints.add(val)
                except: continue

        # Deep Regex for Moodle sub-directories
        patterns = [
            r'https?://lms\.kwasu\.edu\.ng/[\w\.-/]+\.php',
            r'/lib/ajax/[\w\.-]+\.php',
            r'/webservice/rest/[\w\.-]+\.php'
        ]
        for pattern in patterns:
            matches = re.findall(pattern, page_source)
            found_endpoints.update(matches)

        return found_endpoints

    except Exception as e:
        print(f"[!] Critical Error: {e}")
        return []
    finally:
        driver.quit()

# Run discovery
target = "https://lms.kwasu.edu.ng/login/forgot_password.php"
results = discover_with_selenium(target)

print("\n" + "="*50)
print("FINAL ENDPOINT DIRECTORY")
print("="*50)
for r in sorted(results):
    if "kwasu.edu.ng" in r or r.startswith("/"):
        print(r)