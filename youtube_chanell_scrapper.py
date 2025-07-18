import requests
import json
import csv
from datetime import datetime, timedelta
import re
import pandas as pd
from isodate import parse_duration
import time
import logging
from typing import List, Dict, Optional
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class YouTubeChannelScraper:
    def __init__(self, api_key: str):
        
        self.api_key = api_key
        self.base_url = "https://www.googleapis.com/youtube/v3"
        self.session = requests.Session()
        self.request_count = 0
        self.max_requests_per_day = 10000  # YouTube API quota limit
    
    def _make_request(self, url: str, params: dict) -> dict:
        """
        Make API request with error handling and rate limiting
        """
        if self.request_count >= self.max_requests_per_day:
            raise Exception("Daily API quota exceeded")
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            self.request_count += 1
            
            data = response.json()
            
            # Check for API errors
            if 'error' in data:
                raise Exception(f"API Error: {data['error']['message']}")
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise Exception(f"Request failed: {e}")
    
    def extract_channel_id(self, channel_url: str) -> str:
        """
        Extract channel ID from various YouTube URL formats with improved accuracy
        """
        # Clean up the URL
        channel_url = channel_url.strip()
        
        # Handle different URL formats
        patterns = [
            (r'youtube\.com/channel/([a-zA-Z0-9_-]+)', 'channel'),
            (r'youtube\.com/c/([a-zA-Z0-9_-]+)', 'custom'),
            (r'youtube\.com/user/([a-zA-Z0-9_-]+)', 'user'),
            (r'youtube\.com/@([a-zA-Z0-9_.-]+)', 'handle'),
            (r'youtube\.com/([a-zA-Z0-9_-]+)$', 'custom')  # Direct channel name
        ]
        
        for pattern, url_type in patterns:
            match = re.search(pattern, channel_url)
            if match:
                channel_identifier = match.group(1)
                
                # If it's already a channel ID, return it
                if url_type == 'channel':
                    return channel_identifier
                
                # Otherwise, resolve it to a channel ID
                return self.resolve_channel_id(channel_identifier, url_type)
        
        raise ValueError(f"Invalid YouTube channel URL: {channel_url}")
    
    def resolve_channel_id(self, identifier: str, url_type: str) -> str:
        """
        Resolve username, custom URL, or handle to channel ID with improved accuracy
        """
        if url_type == 'user':
            # Legacy username
            url = f"{self.base_url}/channels"
            params = {
                'part': 'id',
                'forUsername': identifier,
                'key': self.api_key
            }
        elif url_type == 'handle':
            # Handle format (@username)
            url = f"{self.base_url}/channels"
            params = {
                'part': 'id',
                'forHandle': identifier,
                'key': self.api_key
            }
        else:
            # Custom URL or channel name - use search
            url = f"{self.base_url}/search"
            params = {
                'part': 'id',
                'q': identifier,
                'type': 'channel',
                'maxResults': 1,
                'key': self.api_key
            }
        
        data = self._make_request(url, params)
        
        if 'items' in data and len(data['items']) > 0:
            item = data['items'][0]
            if url_type == 'custom':
                return item['id']['channelId']
            else:
                return item['id'] if isinstance(item['id'], str) else item['id']['channelId']
        
        raise ValueError(f"Could not resolve channel ID for: {identifier}")
    
    def get_channel_info(self, channel_id: str) -> dict:
        """
        Get detailed channel information
        """
        url = f"{self.base_url}/channels"
        params = {
            'part': 'snippet,statistics,contentDetails,brandingSettings',
            'id': channel_id,
            'key': self.api_key
        }
        
        data = self._make_request(url, params)
        
        if 'items' not in data or len(data['items']) == 0:
            raise ValueError("Channel not found")
        
        channel = data['items'][0]
        
        return {
            'channel_id': channel_id,
            'channel_name': channel['snippet']['title'],
            'channel_description': channel['snippet']['description'][:500] + '...' if len(channel['snippet']['description']) > 500 else channel['snippet']['description'],
            'subscriber_count': int(channel['statistics'].get('subscriberCount', 0)),
            'video_count': int(channel['statistics'].get('videoCount', 0)),
            'view_count': int(channel['statistics'].get('viewCount', 0)),
            'channel_created_date': channel['snippet']['publishedAt'][:10],
            'country': channel['snippet'].get('country', 'Unknown'),
            'custom_url': channel['snippet'].get('customUrl', ''),
            'thumbnail_url': channel['snippet']['thumbnails']['high']['url'],
            'uploads_playlist_id': channel['contentDetails']['relatedPlaylists']['uploads']
        }
    
    def get_channel_videos(self, channel_url: str, max_results: int = 50, sort_by: str = 'date') -> List[dict]:
        """
        Get videos from a YouTube channel with enhanced features
        """
        try:
            channel_id = self.extract_channel_id(channel_url)
            channel_info = self.get_channel_info(channel_id)
            
            logger.info(f"Scraping channel: {channel_info['channel_name']}")
            logger.info(f"Channel has {channel_info['video_count']} total videos")
            
            uploads_playlist_id = channel_info['uploads_playlist_id']
            
            # Get videos from uploads playlist
            videos = []
            next_page_token = None
            
            while len(videos) < max_results:
                playlist_url = f"{self.base_url}/playlistItems"
                playlist_params = {
                    'part': 'snippet',
                    'playlistId': uploads_playlist_id,
                    'maxResults': min(50, max_results - len(videos)),
                    'key': self.api_key
                }
                
                if next_page_token:
                    playlist_params['pageToken'] = next_page_token
                
                data = self._make_request(playlist_url, playlist_params)
                
                if 'items' not in data:
                    break
                
                video_ids = [item['snippet']['resourceId']['videoId'] for item in data['items']]
                
                # Get detailed video statistics
                video_details = self.get_video_details(video_ids, channel_info)
                videos.extend(video_details)
                
                next_page_token = data.get('nextPageToken')
                if not next_page_token:
                    break
                
                logger.info(f"Scraped {len(videos)} videos so far...")
                time.sleep(0.1)  # Rate limiting
            
            # Sort videos if requested
            if sort_by == 'views':
                videos.sort(key=lambda x: x['views'], reverse=True)
            elif sort_by == 'likes':
                videos.sort(key=lambda x: x['likes'], reverse=True)
            
            return videos[:max_results]
            
        except Exception as e:
            logger.error(f"Error: {e}")
            return []
    
    def get_video_details(self, video_ids: List[str], channel_info: dict) -> List[dict]:
        """
        Get detailed information for a list of video IDs with enhanced metrics including thumbnails
        """
        video_url = f"{self.base_url}/videos"
        video_params = {
            'part': 'snippet,statistics,contentDetails,status',
            'id': ','.join(video_ids),
            'key': self.api_key
        }

        data = self._make_request(video_url, video_params)

        videos = []
        for item in data.get('items', []):
            try:
                # Duration processing
                duration_iso = item['contentDetails']['duration']
                duration_seconds = parse_duration(duration_iso).total_seconds()
                duration_minutes = round(duration_seconds / 60, 2)
                
                # Video type classification
                video_type = self._classify_video_type(duration_minutes)
                
                # Statistics
                views = int(item['statistics'].get('viewCount', 0))
                likes = int(item['statistics'].get('likeCount', 0))
                comments = int(item['statistics'].get('commentCount', 0))
                
                # Upload date processing
                upload_date = item['snippet']['publishedAt']
                upload_date_formatted = upload_date[:10]  # YYYY-MM-DD
                days_since_upload = self._calculate_days_since_upload(upload_date)
                
                # Content analysis
                title = item['snippet']['title']
                description = item['snippet']['description']
                
                # Extract thumbnail URLs with multiple quality options
                thumbnails = item['snippet'].get('thumbnails', {})
                thumbnail_urls = self._extract_thumbnail_urls(thumbnails)
                
                video_info = {
                    'title': title,
                    'url': f"https://www.youtube.com/watch?v={item['id']}",
                    'channel_name': channel_info['channel_name'],
                    'views': views,
                    'likes': likes,
                    'comments': comments,
                    'upload_date': upload_date_formatted,
                    'upload_datetime': upload_date,
                    'days_since_upload': days_since_upload,
                    'duration_minutes': duration_minutes,
                    'video_type': video_type,
                    'description': description,
                    'thumbnail_high': thumbnail_urls.get('high', ''),
                    
                }
                
                videos.append(video_info)
                
            except Exception as e:
                logger.error(f"Error processing video {item.get('id', 'unknown')}: {e}")
                continue

        return videos
    
    def _extract_thumbnail_urls(self, thumbnails: dict) -> dict:

        thumbnail_urls = {}
        
        # Define quality priorities (highest to lowest)
        quality_priorities = ['high']
        
        # Extract all available thumbnail qualities
        for quality in quality_priorities:
            if quality in thumbnails:
                thumbnail_urls[quality] = thumbnails[quality]['url']
                break
        
       # Set the best available thumbnail (highest quality)
        for quality in quality_priorities:
            if quality in thumbnail_urls:
                thumbnail_urls['high'] = thumbnail_urls[quality]
                break
        
        return thumbnail_urls
    
    def _classify_video_type(self, duration_minutes: float) -> str:
        """Classify video type based on duration in minutes"""
        if duration_minutes <= 10:
            return 'Low'
        elif duration_minutes <= 30:
            return 'Medium'
        else:
            return 'Long'
    
    def _calculate_days_since_upload(self, upload_date: str) -> int:
        """Calculate days since upload"""
        upload_dt = datetime.fromisoformat(upload_date.replace('Z', '+00:00'))
        now = datetime.now(upload_dt.tzinfo)
        return (now - upload_dt).days
    
    def save_to_excel(self, videos: List[dict], filename: str = 'youtube_data.xlsx'):
        """Save data to Excel with multiple sheets and formatting"""
        if not videos:
            logger.warning("No videos to save")
            return

        # Create Excel writer
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # Main data sheet
            df = pd.DataFrame(videos)
            df.to_excel(writer, sheet_name='Video Data', index=False)
            
            # Create a separate sheet for thumbnail URLs for better readability
           
            
        logger.info(f"Data saved to {filename}")
    
# Enhanced example usage
if __name__ == "__main__":
    # You need to get your API key from Google Cloud Console
    API_KEY = "YOUR_API_KEY_HERE"  # Replace with your actual API key
    
    if API_KEY == "YOUR_API_KEY_HERE":
        print("Please replace 'YOUR_API_KEY_HERE' with your actual YouTube API key")
        print("Get your API key from: https://console.developers.google.com/")
        exit()
    
    # Initialize scraper
    scraper = YouTubeChannelScraper(API_KEY)
    
    print("Enhanced YouTube Channel Scraper")
    print("=" * 50)
    
    # Get user input
    channel_url = input("Enter YouTube channel URL: ").strip()
    max_videos = int(input("Enter maximum number of videos to scrape (default 50): ") or "50")
    
    
    # Scrape videos
    videos = scraper.get_channel_videos(channel_url, max_results=max_videos)
    
    if videos:
        # Display results
        # Export options
        print(f"\n{'='*20} EXPORT OPTIONS {'='*20}")
        save_excel = input("Save data to Excel? (y/n): ").strip().lower()
        if save_excel == 'y':
            excel_filename = input("Enter Excel filename (default: youtube_data.xlsx): ").strip() or "youtube_data.xlsx"
            scraper.save_to_excel(videos, excel_filename)

    print("Scraping completed!")