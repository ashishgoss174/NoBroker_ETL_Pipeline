# -*- coding: utf-8 -*-
"""
Created on Thu Jan 30 16:56:50 2025

@author: hp
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import os
from datetime import datetime

def parse_url(url_element):
    data = {}
    for child in url_element:
        if child.tag.endswith('loc'):
            data['loc'] = child.text
        elif child.tag.endswith('lastmod'):
            data['lastmod'] = child.text
        elif child.tag.endswith('changefreq'):
            data['changefreq'] = child.text
        elif child.tag.endswith('priority'):
            data['priority'] = child.text
    return data

# Function to clean up currency values
def clean_currency(value):
    if value:
        match = re.search(r'(\d[\d,]*)', str(value))
        return int(match.group(1).replace(',', '')) if match else None
    return None

# Function to extract city and state properly
def extract_city_from_url(url):
    # Look for both -for-rent-in- and _cityname patterns
    match = re.search(r'-for-rent-in-([a-z0-9_\-]+)', url.lower())
    if match:
        location_parts = match.group(1).replace('_', '-').split('-')
        # Remove unwanted parts (like 'page', numbers)
        cleaned_parts = [part for part in location_parts if not re.match(r'^(page|\d+)$', part)]
        return cleaned_parts[-1] if cleaned_parts else None
    
    # Handle cases with "_city" format
    match_underscore = re.search(r'properties-for-lease-in-([a-z0-9_\-]+)', url.lower())
    if match_underscore:
        location_parts = match_underscore.group(1).replace('_', '-').split('-')
        return location_parts[-1] if location_parts else None
    
    return None


def extract_locality(text):
    """Extract clean locality name dynamically."""
    # Handle different keywords and clean up the locality text
    delimiters = [' in ', ' with ', ' for ', '-']
    for delimiter in delimiters:
        if delimiter in text:
            cleaned_text = text.split(delimiter)[-1]
            return cleaned_text.strip().replace('_', ' ').title()
    
    # Fallback for cases with no delimiter
    return text.strip().replace('_', ' ').title()



def data_collection():
    start_time = time.time()
    driver = webdriver.Chrome()
    driver.get("https://www.nobroker.in/")
    driver.implicitly_wait(20)
    wait = WebDriverWait(driver, 30)

    all_links = []
    link_texts = []  # List to collect the text of the links

    categories = [ "flats-for-rent-in-","villas-for-rent-in-", "independentfloor-for-rent-in-", "properties-for-lease-in-"]
    
    for category in categories:
        try:
            elements = wait.until(
                EC.presence_of_all_elements_located((By.XPATH, f"//a[contains(@href, '{category}')]"))
            )
            # Collecting both the href and the text of the links
            for el in elements:
                all_links.append(el.get_attribute('href'))
                link_texts.append(el.text.strip())  # Collecting text of the link and stripping any extra whitespace
        except Exception as e:
            print(f"Error fetching links for {category}: {e}")
            
            

    # Ensure the two lists have the same length
    print(f"Number of links extracted: {len(all_links)}")
    
    
    if len(all_links) == len(link_texts):
        print("Extraction is consistent: Number of links matches the number of texts.")
    else:
        print("Mismatch found! Number of links and text elements are different.")
        
    print(f"Total rental links found: {len(all_links)}")
    nobroker_data = []
    
    for link, text in zip(all_links, link_texts):
        locality = extract_locality(text)  # Extract locality from the link text
        city = extract_city_from_url(link)
        
        if(len(locality) < 5):
            print(f"Scraping link: {link} - Locality: {locality} , City: {city}")
        
        try:
            driver.get(link)
            time.sleep(5)  # Wait for JavaScript rendering
        except Exception as e:
            print(f"Error processing link: {e}")


        print(f"Scraping link: {link} - Locality: {locality} , City: {city}")
        try:
            driver.get(link)
            time.sleep(5)  # Wait for JavaScript rendering
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            listings = soup.find_all('article')
            
            for listing in listings:
                try:
                    
                    address_tag = listing.find('meta', {'itemprop': 'name'})
                    address = address_tag['content'].strip() if address_tag else None
                    
                    
                    # Extracting Rent Amount
                    rent_pattern = re.compile(r'^rent.*', re.IGNORECASE)
                    # Find the 'rent' text
                    rent_tag = listing.find(string=rent_pattern)

                    if rent_tag:
                        # Get the parent of the 'rent' text and find its previous sibling
                        rent_div = rent_tag.parent
                        prev_sibling = rent_div.find_previous_sibling("div")
                        
                        # Check if the previous sibling exists and extract its text
                        if prev_sibling:
                            rent_text = prev_sibling.text.strip()
                            
                            # Extract numeric value from the rent text using regex
                            match = re.search(r'(?:Rs\s*)?(\d+(?:,\d+)*)', rent_text)
                            rent = int(match.group(1).replace(',', '')) if match else None
                        else:
                            rent = None
                    else:
                        rent = None
                    
                    # Extracting Deposit Amount
                    deposit_pattern = re.compile(r'^deposit.*', re.IGNORECASE)
                    deposit_tag = listing.find(string = deposit_pattern)

                    if deposit_tag:
                        deposit_div = deposit_tag.parent
                        prev_sibling = deposit_div.find_previous_sibling("div")
                        if prev_sibling:
                            deposit_text = prev_sibling.text.strip()
                            match = re.search(r'(?:Rs\s*)?(\d+(?:,\d+)*)', deposit_text)
                            deposit_amount = int(match.group(1).replace(',', '')) if match else None
                        else:
                            deposit_amount = None
                    else:
                        deposit_amount = None

                    # Extracting Built-up Area
                    area_pattern = re.compile(r'^builtup.*', re.IGNORECASE)
                    area_tag = listing.find(string = area_pattern)

                    if area_tag:
                        area_div = area_tag.parent
                        prev_sibling = area_div.find_previous_sibling("div")
                        builtup = prev_sibling.text.strip() if prev_sibling else None
                    else:
                        builtup = None  
                    
                    # Extracting furnishing details
                    furnish_pattern = re.compile(r'^furnishing.*', re.IGNORECASE)

                    # Find the 'furnishing' text
                    furnish_tag = listing.find(string = furnish_pattern)

                    if furnish_tag:
                        # Get the parent of the 'furnishing' text
                        furnish_div = furnish_tag.parent.parent
                        furnishing = furnish_div.previous_sibling.text.strip()

                    

                    # Extracting appartment typo
                    apt_pattern = re.compile(r'^apartment type.*', re.IGNORECASE)
                    # Find the 'apartment type' text
                    apt_tag = listing.find(string = apt_pattern)

                    if apt_tag:
                        # Get the parent of the 'apartment type' text and find its previous sibling
                        heading_div = apt_tag.parent
                        prev_sibling = heading_div.find_previous_sibling("div")
                        
                        # Check if the previous sibling has the desired class and extract its text
                        if prev_sibling and "font-semibold" in prev_sibling.get("class", []):
                            apt_type = prev_sibling.text.strip()
                        else:
                            apt_type = None
                    else:
                        apt_type = None

                    nobroker_data.append([
                        city ,locality, apt_type, rent, deposit_amount,furnishing, builtup, address,
                        datetime.now().strftime('%Y-%m-%d'), round(time.time() - start_time, 2)
                    ])
                except Exception as e:
                    print(f"Error processing listing: {e}")
        except Exception as e:
            print(f"Error scraping page: {e}")
            
            
    print(f"Finished scraping {len(nobroker_data)} listings.")
    driver.quit()

    # Convert to DataFrame
    columns = ['City', 'Locality', 'Apartment_Type', 'Rent_INR', 'Deposit_INR',
               'Furnishing', 'Area_Sqft', 'Address', 'Relevant_Date', 'Runtime']
    df = pd.DataFrame(nobroker_data, columns=columns)

    return df

# Function to save DataFrame to Excel
def save_to_excel(df, filename):
    if df.empty:
        print("No data to save.")
        return

    file_path = os.path.join("C:\\Users\\hp\\Documents\\thurros\\nobroker", filename)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    df.to_excel(file_path, index=False)
    print(f"Data saved to {file_path}")


# Run the scraper
if __name__ == "__main__":
    nobroker_df = data_collection()
    save_to_excel(nobroker_df, "nobroker_data.xlsx")
