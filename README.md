# Jazz Standards Spotify Scraper

A Python script that scrapes the top 100 jazz standards from [jazzstandards.com](https://www.jazzstandards.com) and creates a curated Spotify playlist with recommended recordings for each standard.

## What it does

This tool automatically:
1. Scrapes the top 100 jazz standards from jazzstandards.com
2. For each standard, finds up to 6 recommended recordings from the website
3. Searches Spotify for each recommended recording
4. Creates a Spotify playlist with all found tracks
5. Uses smart matching to automatically accept obvious matches, reducing user interaction

## Example Output

See an example playlist created by this tool: [Top 100 Jazz Standards - Recommended Recordings](https://open.spotify.com/playlist/2WlqSEDc2j262bHd5l8EHq?si=e724e67fd9254e46)

## Requirements

- Python 3.6+
- Required packages:
  ```bash
  pip install spotipy beautifulsoup4 requests
  ```

## Setup

1. Create a Spotify app at https://developer.spotify.com/dashboard
2. Update `config.py` with your Spotify app credentials:
   ```python
   CLIENT_ID = "your_client_id_here"
   CLIENT_SECRET = "your_client_secret_here"
   REDIRECT_URI = "http://127.0.0.1:8888/callback"
   ```

## Usage

```bash
python jazz_standards_playlist.py
```

The script will:
- Authenticate with Spotify (browser window will open on first run)
- Scrape jazz standards and their recommended recordings
- Search for tracks on Spotify
- Create a new playlist in your Spotify account
- Automatically accept strong matches (same artist + song title)
- Ask for confirmation only on uncertain matches

## Features

- **Smart matching**: Automatically accepts tracks when artist and song title match closely
- **Rate limiting**: Respectful 0.5 second delays between requests
- **Batch processing**: Adds tracks to playlist in batches to handle Spotify API limits
- **Duplicate prevention**: Avoids adding the same track multiple times
- **Progress tracking**: Shows detailed progress as it processes each standard

## Configuration

The script processes the top 100 jazz standards and finds up to 6 recommended recordings per standard. You can modify these limits in the code if needed.