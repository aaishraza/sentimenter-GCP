# File: scraper.py
# This is the correct and final version for the GCP VM.

import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

def get_driver():
    """
    Initializes a WebDriver for a full Linux VM.
    Uses webdriver-manager to automatically handle the chromedriver.
    """
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    # Use webdriver-manager to install and manage the driver automatically
    service = Service(ChromeDriverManager().install())
    
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def scrape_reviews(url, status_placeholder):
    """
    Scrapes reviews and returns a DataFrame and an optional screenshot path.
    The status_placeholder is a dummy class to print logs on the server console.
    """
    driver = get_driver()
    reviews_data = []
    screenshot_path = "debug_screenshot.png"
    
    try:
        status_placeholder.text(f"Navigating to URL: {url}")
        driver.get(url)
        
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.ID, "module_product_review")))
        
        page_num = 1
        while True:
            status_placeholder.text(f"Scraping page {page_num}...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            review_items = soup.select('div.mod-reviews div.item')
            if not review_items:
                status_placeholder.text("No review items found on this page. Finishing up.")
                break
            for item in review_items:
                name_element = item.select_one('div.middle > span:first-child')
                reviewer_name = name_element.text.strip() if name_element else "Anonymous"
                content_element = item.select_one('div.content')
                review_text = content_element.text.strip() if content_element else "No Text"
                filled_stars = item.select('div.top img[src*="TB19ZvEgfDH8KJjy1XcXXa-64-64.png"]')
                rating = len(filled_stars)
                reviews_data.append({'Reviewer': reviewer_name, 'Rating': rating, 'Review Text': review_text})
            try:
                next_btn = driver.find_element(By.CSS_SELECTOR, ".next-btn.next")
                if "disabled" in next_btn.get_attribute("class"):
                    status_placeholder.text("Reached the last page of reviews.")
                    break
                driver.execute_script("arguments[0].click();", next_btn)
                page_num += 1
            except NoSuchElementException:
                status_placeholder.text("No 'next' button found. Scraping complete.")
                break
            except Exception as e:
                status_placeholder.error(f"Error during pagination: {e}")
                break
    
    except TimeoutException:
        status_placeholder.error("Timed out waiting for review section. This often indicates a CAPTCHA or block.")
        driver.save_screenshot(screenshot_path)
        driver.quit()
        return pd.DataFrame(), screenshot_path

    except Exception as e:
        status_placeholder.error(f"An unexpected error occurred: {e}")
        driver.save_screenshot(screenshot_path)
        driver.quit()
        return pd.DataFrame(), screenshot_path
    
    if reviews_data:
        df = pd.DataFrame(reviews_data).drop_duplicates()
        driver.quit()
        return df, None
    else:
        status_placeholder.error("Scraping finished, but no reviews were collected.")
        driver.save_screenshot(screenshot_path)
        driver.quit()
        return pd.DataFrame(), screenshot_path
scraper.py
