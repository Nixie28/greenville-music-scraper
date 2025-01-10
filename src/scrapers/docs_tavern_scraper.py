import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any
from .base_scraper import BaseScraper
import json
import re

class DocsTavernScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            venue_name="Doc's Tavern",
            base_url='https://docstavernsc.com/calendar/'
        )

    def parse_event_time(self, time_str: str) -> str:
        """Parse event time from various formats"""
        time_str = time_str.strip().lower()
        # Remove @ symbol and clean up
        time_str = time_str.replace('@', '').strip()
        return time_str

    async def scrape_events(self) -> List[Dict[str, Any]]:
        events = []
        
        async with aiohttp.ClientSession() as session:
            try:
                # Fetch the main calendar page
                async with session.get(self.base_url, headers=self.headers) as response:
                    if response.status != 200:
                        print(f"Error fetching Doc's Tavern calendar: {response.status}")
                        return events

                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Find all event entries - they typically use tribe-events-calendar classes
                    event_elements = soup.select('.tribe-events-calendar-list__event-row')
                    
                    for event_element in event_elements:
                        try:
                            # Extract event details
                            title_elem = event_element.select_one('.tribe-events-calendar-list__event-title')
                            date_elem = event_element.select_one('.tribe-events-calendar-list__event-datetime')
                            desc_elem = event_element.select_one('.tribe-events-calendar-list__event-description')
                            link_elem = event_element.select_one('.tribe-events-calendar-list__event-title-link')
                            
                            if not title_elem or not date_elem:
                                continue

                            event_data = {
                                'venue': self.venue_name,
                                'title': self.clean_text(title_elem.text),
                                'date': self.clean_text(date_elem.text),
                                'url': link_elem['href'] if link_elem else self.base_url,
                                'description': self.clean_text(desc_elem.text) if desc_elem else '',
                            }

                            # Some events might have additional details like price
                            price_elem = event_element.select_one('.tribe-events-c-small-cta__price')
                            if price_elem:
                                event_data['price'] = self.clean_text(price_elem.text)
                            else:
                                event_data['price'] = 'Contact venue for price'

                            events.append(event_data)
                            
                        except Exception as e:
                            print(f"Error parsing event: {str(e)}")
                            continue

            except Exception as e:
                print(f"Error scraping Doc's Tavern: {str(e)}")
                
        return events

    async def get_event_details(self, event_url: str) -> Dict[str, Any]:
        """Get additional details from event page"""
        async with aiohttp.ClientSession() as session:
            async with session.get(event_url, headers=self.headers) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                details = {}
                
                # Look for structured data
                script_tag = soup.find('script', {'type': 'application/ld+json'})
                if script_tag:
                    try:
                        json_data = json.loads(script_tag.string)
                        if isinstance(json_data, dict):
                            details['start_date'] = json_data.get('startDate')
                            details['end_date'] = json_data.get('endDate')
                            details['price'] = json_data.get('price')
                    except:
                        pass
                
                return details
