import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import json
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Tuple
import re
import sqlite3
from datetime import datetime

class ArtistManager:
    def __init__(self, db_path='artists.db'):
        self.db_path = db_path
        self.setup_database()
        
        # Initialize Spotify client
        try:
            self.spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
        except:
            self.spotify = None
            print("Warning: Spotify API not configured")

    def setup_database(self):
        """Create SQLite database for artists"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Artists table
        c.execute('''CREATE TABLE IF NOT EXISTS artists
                    (id INTEGER PRIMARY KEY,
                     name TEXT UNIQUE,
                     is_local BOOLEAN,
                     verification_source TEXT,
                     last_updated DATETIME)''')
        
        # Genres table
        c.execute('''CREATE TABLE IF NOT EXISTS artist_genres
                    (artist_id INTEGER,
                     genre TEXT,
                     confidence FLOAT,
                     source TEXT,
                     FOREIGN KEY(artist_id) REFERENCES artists(id))''')
        
        # Venues table
        c.execute('''CREATE TABLE IF NOT EXISTS artist_venues
                    (artist_id INTEGER,
                     venue TEXT,
                     last_played DATETIME,
                     FOREIGN KEY(artist_id) REFERENCES artists(id))''')
        
        conn.commit()
        conn.close()

    async def process_artist(self, artist_name: str, venue: str = None) -> Dict:
        """Main function to process an artist and get their information"""
        # Check database first
        artist_info = self.get_artist_from_db(artist_name)
        if artist_info:
            # Update venue information
            if venue:
                self.update_venue_info(artist_info['id'], venue)
            return artist_info

        # If not in database, gather information from various sources
        artist_info = await self.gather_artist_info(artist_name, venue)
        self.save_artist_to_db(artist_info)
        return artist_info

    async def gather_artist_info(self, artist_name: str, venue: str = None) -> Dict:
        """Gather artist information from multiple sources"""
        info = {
            'name': artist_name,
            'genres': [],
            'is_local': False,
            'confidence': 0.0,
            'sources': []
        }

        # Try Spotify first
        if self.spotify:
            spotify_info = self.get_spotify_info(artist_name)
            if spotify_info:
                info.update(spotify_info)
                info['sources'].append('spotify')

        # Check social media
        social_info = await self.check_social_media(artist_name)
        if social_info:
            info['is_local'] = info['is_local'] or social_info.get('is_local', False)
            if social_info.get('genres'):
                info['genres'].extend(social_info['genres'])
            info['sources'].extend(social_info.get('sources', []))

        # Check local venue histories
        venue_info = await self.check_venue_history(artist_name)
        if venue_info:
            info['is_local'] = info['is_local'] or venue_info.get('is_local', False)
            if venue_info.get('genres'):
                info['genres'].extend(venue_info['genres'])
            info['sources'].extend(venue_info.get('sources', []))

        # Add current venue if provided
        if venue:
            self.update_venue_info(info['id'], venue)

        return info

    def get_spotify_info(self, artist_name: str) -> Optional[Dict]:
        """Get artist information from Spotify"""
        if not self.spotify:
            return None

        try:
            results = self.spotify.search(q=artist_name, type='artist', limit=1)
            if results['artists']['items']:
                artist = results['artists']['items'][0]
                return {
                    'genres': artist['genres'],
                    'popularity': artist['popularity'],
                    'spotify_id': artist['id'],
                    'confidence': 0.8 if artist['name'].lower() == artist_name.lower() else 0.5
                }
        except Exception as e:
            print(f"Spotify API error: {str(e)}")
        return None

    async def check_social_media(self, artist_name: str) -> Optional[Dict]:
        """Check social media for artist information"""
        info = {'genres': [], 'sources': [], 'is_local': False}
        
        # Clean artist name for searching
        search_name = artist_name.replace(" ", "+")
        
        # Check Instagram for location/bio
        try:
            # This would need to be implemented with proper Instagram API access
            pass
        except Exception as e:
            print(f"Instagram API error: {str(e)}")

        # Check Facebook for events/location
        try:
            # This would need to be implemented with proper Facebook API access
            pass
        except Exception as e:
            print(f"Facebook API error: {str(e)}")

        return info if info['sources'] else None

    async def check_venue_history(self, artist_name: str) -> Optional[Dict]:
        """Check local venue websites for artist history"""
        venues = [
            "https://www.radioroomgreenville.com",
            "https://www.peacecenter.org",
            "https://docstavernsc.com"
        ]
        
        info = {'genres': [], 'sources': [], 'is_local': False}
        
        for venue_url in venues:
            try:
                # Implementation would need proper venue-specific scraping
                pass
            except Exception as e:
                print(f"Venue scraping error for {venue_url}: {str(e)}")

        return info if info['sources'] else None

    def save_artist_to_db(self, artist_info: Dict):
        """Save artist information to database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            # Insert artist
            c.execute('''INSERT INTO artists (name, is_local, verification_source, last_updated)
                        VALUES (?, ?, ?, ?)''',
                     (artist_info['name'], artist_info['is_local'],
                      ','.join(artist_info['sources']), datetime.now()))
            
            artist_id = c.lastrowid
            
            # Insert genres
            for genre in set(artist_info['genres']):
                c.execute('''INSERT INTO artist_genres (artist_id, genre, confidence, source)
                            VALUES (?, ?, ?, ?)''',
                         (artist_id, genre, artist_info['confidence'],
                          ','.join(artist_info['sources'])))
            
            conn.commit()
        except Exception as e:
            print(f"Database error: {str(e)}")
            conn.rollback()
        finally:
            conn.close()

    def get_artist_from_db(self, artist_name: str) -> Optional[Dict]:
        """Retrieve artist information from database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            c.execute('''SELECT * FROM artists WHERE name = ?''', (artist_name,))
            artist = c.fetchone()
            
            if artist:
                # Get genres
                c.execute('''SELECT genre FROM artist_genres WHERE artist_id = ?''',
                         (artist[0],))
                genres = [row[0] for row in c.fetchall()]
                
                # Get venues
                c.execute('''SELECT venue, last_played FROM artist_venues 
                           WHERE artist_id = ?''', (artist[0],))
                venues = [(row[0], row[1]) for row in c.fetchall()]
                
                return {
                    'id': artist[0],
                    'name': artist[1],
                    'is_local': artist[2],
                    'verification_source': artist[3],
                    'last_updated': artist[4],
                    'genres': genres,
                    'venues': venues
                }
        except Exception as e:
            print(f"Database error: {str(e)}")
        finally:
            conn.close()
        
        return None

    def update_venue_info(self, artist_id: int, venue: str):
        """Update venue information for an artist"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            c.execute('''INSERT INTO artist_venues (artist_id, venue, last_played)
                        VALUES (?, ?, ?)''', (artist_id, venue, datetime.now()))
            conn.commit()
        except Exception as e:
            print(f"Database error: {str(e)}")
            conn.rollback()
        finally:
            conn.close()