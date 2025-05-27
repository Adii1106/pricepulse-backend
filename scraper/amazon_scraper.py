import requests
from bs4 import BeautifulSoup
import re
from typing import Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AmazonScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    async def scrape_product(self, url: str) -> dict:
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract product name
            name = soup.find('span', {'id': 'productTitle'})
            name = name.text.strip() if name else "Product Name Not Found"

            # Extract price
            price = None
            price_element = soup.find('span', {'class': 'a-price-whole'})
            if price_element:
                price_text = price_element.text.strip()
                # Remove any non-numeric characters except decimal point
                price = float(re.sub(r'[^\d.]', '', price_text))
            else:
                price = 0.0

            # Extract image URL
            image = soup.find('img', {'id': 'landingImage'})
            image_url = image.get('data-old-hires') if image else None

            return {
                "name": name,
                "price": price,
                "image_url": image_url
            }
        except Exception as e:
            print(f"Error scraping product: {str(e)}")
            return {
                "name": "Error",
                "price": 0.0,
                "image_url": None
            }

    async def _get_product_name(self, page) -> Optional[str]:
        """Extract product name from the page"""
        try:
            # Try different selectors for product name
            selectors = [
                '#productTitle',
                '#title',
                'h1.a-size-large'
            ]
            
            for selector in selectors:
                element = await page.query_selector(selector)
                if element:
                    name = await element.text_content()
                    return name.strip()
            
            return None
        except Exception as e:
            logger.error(f"Error getting product name: {str(e)}")
            return None

    async def _get_product_price(self, page) -> Optional[str]:
        """Extract product price from the page"""
        try:
            # Try different selectors for price
            selectors = [
                '.a-price .a-offscreen',
                '#priceblock_ourprice',
                '#priceblock_dealprice',
                '.a-price-whole'
            ]
            
            for selector in selectors:
                element = await page.query_selector(selector)
                if element:
                    price_text = await element.text_content()
                    # Extract numeric price using regex
                    price_match = re.search(r'[\d,]+\.?\d*', price_text)
                    if price_match:
                        return price_match.group()
            
            return None
        except Exception as e:
            logger.error(f"Error getting product price: {str(e)}")
            return None

    async def _get_product_image(self, page) -> Optional[str]:
        """Extract product image URL from the page"""
        try:
            # Try different selectors for product image
            selectors = [
                '#landingImage',
                '#imgBlkFront',
                '.a-dynamic-image'
            ]
            
            for selector in selectors:
                element = await page.query_selector(selector)
                if element:
                    image_url = await element.get_attribute('src')
                    if image_url:
                        return image_url
            
            return None
        except Exception as e:
            logger.error(f"Error getting product image: {str(e)}")
            return None 