import pandas as pd
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any
import asyncio
import re

class DocsTavernEventProcessor:
    def __init__(self):
        self.base_url = 'https://docstavernsc.com/calendar/'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    async def scrape_events(self) -> List[Dict[str, Any]]:
        events = []
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(self.base_url, headers=self.headers) as response:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    event_elements = soup.select('.tribe-events-calendar-list__event-row')
                    
                    for event in event_elements:
                        try:
                            # Basic event info
                            title_elem = event.select_one('.tribe-events-calendar-list__event-title')
                            date_elem = event.select_one('.tribe-events-calendar-list__event-datetime')
                            desc_elem = event.select_one('.tribe-events-calendar-list__event-description')
                            ticket_link = event.select_one('a[href*="ticket"]')
                            
                            # Get the full event details URL
                            event_url = event.select_one('.tribe-events-calendar-list__event-title-link')
                            
                            # Extract genre from description or title
                            genre = self.extract_genre(desc_elem.text if desc_elem else title_elem.text)
                            
                            # Determine if event is free or needs tickets
                            ticket_info = self.get_ticket_info(event, ticket_link)
                            
                            event_data = {
                                'venue': "Doc's Tavern",
                                'band_name': self.clean_text(title_elem.text) if title_elem else 'TBA',
                                'date_time': self.clean_text(date_elem.text) if date_elem else 'TBA',
                                'genre': genre,
                                'ticket_status': ticket_info['status'],
                                'ticket_link': ticket_info['link']
                            }
                            
                            events.append(event_data)
                            
                        except Exception as e:
                            print(f"Error parsing event: {str(e)}")
                            continue
                            
            except Exception as e:
                print(f"Error accessing Doc's Tavern calendar: {str(e)}")
                
        return events
    
    def extract_genre(self, text: str) -> str:
        """Extract genre from text using common genre keywords"""
        genres = {
            'rock': ['rock', 'alternative', 'punk', 'metal'],
            'country': ['country', 'bluegrass', 'americana'],
            'jazz': ['jazz', 'blues', 'soul'],
            'pop': ['pop', 'indie', 'electronic'],
            'hip hop': ['hip hop', 'rap', 'r&b']
        }
        
        text = text.lower()
        for genre, keywords in genres.items():
            if any(keyword in text for keyword in keywords):
                return genre.title()
        return 'Various/Unknown'
    
    def get_ticket_info(self, event_elem, ticket_link) -> Dict[str, str]:
        """Determine ticket status and get link if available"""
        text = event_elem.text.lower()
        
        if 'free' in text:
            return {'status': 'Free', 'link': ''}
        elif ticket_link:
            return {'status': 'Tickets Required', 'link': ticket_link['href']}
        else:
            return {'status': 'Contact Venue', 'link': self.base_url}
    
    def clean_text(self, text: str) -> str:
        """Clean and standardize text"""
        return ' '.join(text.split()).strip()
    
    def export_to_excel(self, events: List[Dict[str, Any]], filename: str = 'live_music_events.xlsx'):
        """Export events to Excel spreadsheet"""
        df = pd.DataFrame(events)
        df = df[['venue', 'band_name', 'date_time', 'genre', 'ticket_status', 'ticket_link']]
        df.columns = ['Venue', 'Band Name', 'Date & Time', 'Genre', 'Ticket Status', 'Ticket Link']
        
        # Sort by date
        df['Date & Time'] = pd.to_datetime(df['Date & Time'], format='mixed')
        df = df.sort_values('Date & Time')
        
        # Format date for display
        df['Date & Time'] = df['Date & Time'].dt.strftime('%Y-%m-%d %I:%M %p')
        
        df.to_excel(filename, index=False)
        print(f"Events exported to {filename}")

async def main():
    processor = DocsTavernEventProcessor()
    events = await processor.scrape_events()
    processor.export_to_excel(events)

if __name__ == "__main__":
    asyncio.run(main())