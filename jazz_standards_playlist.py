import requests
from bs4 import BeautifulSoup
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
import re
from typing import List, Dict, Optional
import logging from config import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class JazzStandardsSpotifyPlaylist:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str = "http://127.0.0.1:8888/callback"):
        """
        Initialize the scraper and Spotify client
        
        Args:
            client_id: Spotify app client ID
            client_secret: Spotify app client secret
            redirect_uri: Redirect URI for Spotify OAuth
        """
        self.base_url = "https://www.jazzstandards.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Initialize Spotify client
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope="playlist-modify-public playlist-modify-private"
        ))
        
        self.user_id = self.sp.current_user()["id"]
        
    def scrape_top_100_standards(self) -> List[Dict[str, str]]:
        """
        Scrape the top 100 jazz standards from jazzstandards.com
        
        Returns:
            List of dictionaries containing standard info
        """
        standards = []
        
        try:
            # The top 100 list is on the main compositions page
            response = requests.get(f"{self.base_url}/compositions/index.htm", headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the standards list - actual pattern from jazzstandards.com
            standard_links = soup.find_all('a', href=re.compile(r'compositions-0/.*\.htm'))[:100]
            
            for link in standard_links:
                standard = {
                    'title': link.get_text(strip=True),
                    'url': self.base_url + link.get('href') if not link.get('href').startswith('http') else link.get('href')
                }
                standards.append(standard)
                logger.info(f"Found standard: {standard['title']}")
                
        except Exception as e:
            logger.error(f"Error scraping top 100 list: {e}")
            
        return standards
    
    def scrape_recommended_recordings(self, standard_url: str) -> List[Dict[str, str]]:
        """
        Scrape recommended recordings for a specific jazz standard
        
        Args:
            standard_url: URL of the jazz standard page
            
        Returns:
            List of recommended recordings
        """
        recordings = []
        
        try:
            response = requests.get(standard_url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for recommended recordings section
            # The site embeds recording info in the text content
            recordings_section = soup.find(string=re.compile(r'Recommended Recordings', re.I))
            
            # Parse recording information from the page text
            text_content = soup.get_text()
            
            # Look for artist names followed by recording info
            # Common patterns: "Artist Name (Year)" or "Artist Name - Album/Song"
            artist_patterns = [
                r'([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*\((\d{4})',  # Artist (Year)
                r'([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*[-–]\s*([^(]+)',  # Artist - Info
                r'([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+and\s+His\s+Orchestra',  # Big Band format
            ]
            
            for pattern in artist_patterns:
                matches = re.findall(pattern, text_content)
                for match in matches:
                    if len(match) >= 2:
                        recordings.append({
                            'artist': match[0].strip(),
                            'info': match[1].strip() if len(match) > 1 else '',
                            'full_text': ' - '.join(match)
                        })
                    elif len(match) == 1:
                        recordings.append({
                            'artist': match[0].strip(),
                            'info': '',
                            'full_text': match[0]
                        })
            
            # Remove duplicates
            seen = set()
            unique_recordings = []
            for recording in recordings:
                key = recording['artist'].lower()
                if key not in seen:
                    seen.add(key)
                    unique_recordings.append(recording)
            
            recordings = unique_recordings[:6]  # Limit to 6 recordings
                        
        except Exception as e:
            logger.error(f"Error scraping recordings from {standard_url}: {e}")
            
        # Add small delay to be respectful to the server
        time.sleep(0.5)
        
        return recordings
    
    def search_spotify_track(self, standard_title: str, artist: str, recording_info: str) -> Optional[str]:
        """
        Search for a track on Spotify with automatic acceptance for strong matches
        
        Args:
            standard_title: Title of the jazz standard
            artist: Artist name
            recording_info: Additional recording info
            
        Returns:
            Spotify track URI if found and accepted, None otherwise
        """
        try:
            print(f"\n🎵 Searching for: '{standard_title}' by {artist}")
            if recording_info:
                print(f"   Additional info: {recording_info}")
            
            # Try different search strategies
            queries = [
                f"{artist} {standard_title}",
                f"{artist} {recording_info}",
                f"{standard_title} {artist}"
            ]
            
            for query in queries:
                results = self.sp.search(q=query, type='track', limit=10)
                
                if results['tracks']['items']:
                    # Try to find best match
                    best_match = None
                    is_strong_match = False
                    
                    for track in results['tracks']['items']:
                        track_name = track['name'].lower()
                        artist_names = [a['name'].lower() for a in track['artists']]
                        
                        # Check for strong match: artist name matches and song title matches
                        artist_match = any(artist.lower() in artist_name or artist_name in artist.lower() for artist_name in artist_names)
                        title_match = any(word in track_name for word in standard_title.lower().split()) or standard_title.lower() in track_name
                        
                        if artist_match and title_match:
                            best_match = track
                            is_strong_match = True
                            break
                    
                    # If no strong match, try to find best available match
                    if not best_match:
                        for track in results['tracks']['items']:
                            track_name = track['name'].lower()
                            artist_names = [a['name'].lower() for a in track['artists']]
                            
                            # Check if standard title is in track name
                            if any(word in track_name for word in standard_title.lower().split()):
                                # Check if artist matches
                                if any(artist.lower() in artist_name for artist_name in artist_names):
                                    best_match = track
                                    break
                    
                    # If still no match, use first result
                    if not best_match:
                        best_match = results['tracks']['items'][0]
                    
                    track_artist = best_match['artists'][0]['name']
                    track_name = best_match['name']
                    album_name = best_match['album']['name']
                    
                    print(f"✅ Found match: {track_artist} - {track_name}")
                    print(f"   Album: {album_name}")
                    
                    # Auto-accept strong matches
                    if is_strong_match:
                        print("   🎯 Strong match detected - automatically accepted!")
                        logger.info(f"Auto-accepted strong match: {track_artist} - {track_name}")
                        return best_match['uri']
                    
                    # Ask user for confirmation on weaker matches
                    while True:
                        response = input("   Accept this match? (y/n/s to skip all for this song): ").lower().strip()
                        if response in ['y', 'yes']:
                            logger.info(f"User accepted: {track_artist} - {track_name}")
                            return best_match['uri']
                        elif response in ['n', 'no']:
                            print("   Skipping this match, looking for alternatives...")
                            break
                        elif response in ['s', 'skip']:
                            print("   Skipping all matches for this song...")
                            return None
                        else:
                            print("   Please enter 'y' (yes), 'n' (no), or 's' (skip)")
            
            print("❌ No suitable matches found on Spotify")
            return None
                    
        except Exception as e:
            logger.error(f"Error searching Spotify for {artist} - {standard_title}: {e}")
            return None
    
    def create_playlist(self, playlist_name: str = "Top 100 Jazz Standards - Recommended Recordings") -> str:
        """
        Create a new Spotify playlist
        
        Args:
            playlist_name: Name for the playlist
            
        Returns:
            Playlist ID
        """
        playlist = self.sp.user_playlist_create(
            self.user_id,
            playlist_name,
            public=True,
            description="Recommended recordings of the top 100 jazz standards from jazzstandards.com"
        )
        logger.info(f"Created playlist: {playlist_name}")
        logger.info(f"Playlist URL: {playlist['external_urls']['spotify']}")
        return playlist['id']
    
    def run(self):
        """
        Main execution method
        """
        logger.info("Starting Jazz Standards to Spotify playlist creation...")
        
        # Step 1: Scrape top 100 standards
        logger.info("Scraping top 100 jazz standards...")
        standards = self.scrape_top_100_standards()
        
        if not standards:
            logger.error("No standards found. Please check the website structure.")
            return
        
        logger.info(f"Found {len(standards)} standards")
        
        # Step 2: Create playlist
        playlist_id = self.create_playlist()
        
        # Step 3: Process each standard
        all_track_uris = []
        
        for i, standard in enumerate(standards):
            print(f"\n{'='*60}")
            print(f"📖 Processing {i+1}/{len(standards)}: {standard['title']}")
            print(f"{'='*60}")
            
            # Get recommended recordings
            recordings = self.scrape_recommended_recordings(standard['url'])
            
            if recordings:
                print(f"Found {len(recordings)} recommended recordings for '{standard['title']}'")
            else:
                print(f"No recordings found for '{standard['title']}'")
                continue
            
            # Search for each recording on Spotify
            for j, recording in enumerate(recordings):
                print(f"\n--- Recording {j+1}/{len(recordings)} ---")
                track_uri = self.search_spotify_track(
                    standard['title'],
                    recording['artist'],
                    recording['info']
                )
                
                if track_uri and track_uri not in all_track_uris:
                    all_track_uris.append(track_uri)
                    print(f"✅ Added to playlist!")
                elif track_uri:
                    print(f"⚠️  Already in playlist, skipping duplicate")
            
            # Add tracks to playlist in batches
            if len(all_track_uris) >= 50:
                self.add_tracks_to_playlist(playlist_id, all_track_uris[:50])
                all_track_uris = all_track_uris[50:]
        
        # Add remaining tracks
        if all_track_uris:
            self.add_tracks_to_playlist(playlist_id, all_track_uris)
        
        # Final summary
        print(f"\n{'='*60}")
        print(f"🎉 PLAYLIST CREATION COMPLETE!")
        print(f"{'='*60}")
        print(f"📊 Statistics:")
        print(f"   - Jazz standards processed: {len(standards)}")
        print(f"   - Tracks added to playlist: {len(all_track_uris)}")
        print(f"   - You can find your playlist in the Spotify app or at the URL shown above.")
        print(f"{'='*60}")
        
        logger.info(f"Playlist creation complete! Added {len(all_track_uris)} tracks.")
        logger.info("You can find your playlist in the Spotify app or at the URL shown above.")
        
    def add_tracks_to_playlist(self, playlist_id: str, track_uris: List[str]):
        """
        Add tracks to playlist (Spotify limits to 100 tracks per request)
        
        Args:
            playlist_id: Spotify playlist ID
            track_uris: List of Spotify track URIs
        """
        try:
            self.sp.playlist_add_items(playlist_id, track_uris)
            logger.info(f"Added {len(track_uris)} tracks to playlist")
        except Exception as e:
            logger.error(f"Error adding tracks to playlist: {e}")


def main():
    # Configuration
    # You need to create a Spotify app at https://developer.spotify.com/dashboard
    
    # Create and run the scraper
    scraper = JazzStandardsSpotifyPlaylist(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)
    scraper.run()


if __name__ == "__main__":
    main()
