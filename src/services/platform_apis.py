"""
Platform API Integration Services
Handles connections to external review platforms (Google, Yelp, Facebook, TripAdvisor)
"""

import requests
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod
import os
from urllib.parse import urlencode

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ReviewData:
    """Standardized review data structure"""
    platform: str
    platform_review_id: str
    reviewer_name: str
    reviewer_avatar: Optional[str]
    rating: float
    review_text: str
    review_date: datetime
    location_id: str
    location_name: str
    response_text: Optional[str] = None
    response_date: Optional[datetime] = None
    sentiment: Optional[str] = None
    language: str = 'en'
    verified: bool = False
    helpful_count: int = 0
    photos: List[str] = None

    def __post_init__(self):
        if self.photos is None:
            self.photos = []

@dataclass
class LocationData:
    """Standardized location data structure"""
    platform: str
    platform_location_id: str
    name: str
    address: str
    phone: Optional[str]
    website: Optional[str]
    category: str
    rating: float
    review_count: int
    photos: List[str] = None
    hours: Dict[str, str] = None

    def __post_init__(self):
        if self.photos is None:
            self.photos = []
        if self.hours is None:
            self.hours = {}

class PlatformAPIBase(ABC):
    """Base class for platform API integrations"""
    
    def __init__(self, api_key: str, **kwargs):
        self.api_key = api_key
        self.session = requests.Session()
        self.base_url = self.get_base_url()
        self.setup_authentication(**kwargs)
    
    @abstractmethod
    def get_base_url(self) -> str:
        """Return the base URL for the platform API"""
        pass
    
    @abstractmethod
    def setup_authentication(self, **kwargs):
        """Setup authentication for the platform"""
        pass
    
    @abstractmethod
    def get_reviews(self, location_id: str, limit: int = 50, offset: int = 0) -> List[ReviewData]:
        """Fetch reviews for a location"""
        pass
    
    @abstractmethod
    def get_location_info(self, location_id: str) -> LocationData:
        """Get location information"""
        pass
    
    @abstractmethod
    def post_response(self, review_id: str, response_text: str) -> bool:
        """Post a response to a review"""
        pass
    
    def make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated request to platform API"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON response: {e}")
            raise

class GoogleMyBusinessAPI(PlatformAPIBase):
    """Google My Business API integration"""
    
    def get_base_url(self) -> str:
        return "https://mybusiness.googleapis.com/v4"
    
    def setup_authentication(self, **kwargs):
        """Setup OAuth2 authentication for GMB"""
        self.access_token = kwargs.get('access_token')
        if self.access_token:
            self.session.headers.update({
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            })
    
    def get_reviews(self, location_id: str, limit: int = 50, offset: int = 0) -> List[ReviewData]:
        """Fetch reviews from Google My Business"""
        try:
            endpoint = f"accounts/{self.account_id}/locations/{location_id}/reviews"
            params = {
                'pageSize': min(limit, 50),  # GMB max is 50
                'orderBy': 'updateTime desc'
            }
            
            response = self.make_request('GET', endpoint, params=params)
            reviews = []
            
            for review_data in response.get('reviews', []):
                review = ReviewData(
                    platform='google',
                    platform_review_id=review_data['reviewId'],
                    reviewer_name=review_data['reviewer']['displayName'],
                    reviewer_avatar=review_data['reviewer'].get('profilePhotoUrl'),
                    rating=float(review_data['starRating']),
                    review_text=review_data.get('comment', ''),
                    review_date=datetime.fromisoformat(review_data['updateTime'].replace('Z', '+00:00')),
                    location_id=location_id,
                    location_name=self.get_location_name(location_id),
                    response_text=review_data.get('reviewReply', {}).get('comment'),
                    response_date=datetime.fromisoformat(review_data.get('reviewReply', {}).get('updateTime', '').replace('Z', '+00:00')) if review_data.get('reviewReply', {}).get('updateTime') else None,
                    verified=True,  # GMB reviews are verified
                    language=review_data.get('comment', {}).get('language', 'en') if isinstance(review_data.get('comment'), dict) else 'en'
                )
                reviews.append(review)
            
            return reviews
            
        except Exception as e:
            logger.error(f"Error fetching Google reviews: {e}")
            return []
    
    def get_location_info(self, location_id: str) -> LocationData:
        """Get Google My Business location information"""
        try:
            endpoint = f"accounts/{self.account_id}/locations/{location_id}"
            response = self.make_request('GET', endpoint)
            
            location = LocationData(
                platform='google',
                platform_location_id=location_id,
                name=response['locationName'],
                address=self._format_address(response.get('address', {})),
                phone=response.get('primaryPhone'),
                website=response.get('websiteUrl'),
                category=response.get('primaryCategory', {}).get('displayName', 'Business'),
                rating=float(response.get('averageRating', 0)),
                review_count=int(response.get('reviewCount', 0)),
                photos=[photo['googleUrl'] for photo in response.get('photos', [])[:5]]
            )
            
            return location
            
        except Exception as e:
            logger.error(f"Error fetching Google location info: {e}")
            raise
    
    def post_response(self, review_id: str, response_text: str) -> bool:
        """Post response to Google review"""
        try:
            endpoint = f"accounts/{self.account_id}/locations/{self.location_id}/reviews/{review_id}/reply"
            data = {'comment': response_text}
            
            self.make_request('PUT', endpoint, json=data)
            return True
            
        except Exception as e:
            logger.error(f"Error posting Google review response: {e}")
            return False
    
    def _format_address(self, address_data: Dict) -> str:
        """Format address from GMB address object"""
        parts = []
        if address_data.get('addressLines'):
            parts.extend(address_data['addressLines'])
        if address_data.get('locality'):
            parts.append(address_data['locality'])
        if address_data.get('administrativeArea'):
            parts.append(address_data['administrativeArea'])
        if address_data.get('postalCode'):
            parts.append(address_data['postalCode'])
        return ', '.join(parts)
    
    def get_location_name(self, location_id: str) -> str:
        """Get location name for review data"""
        try:
            location = self.get_location_info(location_id)
            return location.name
        except:
            return "Unknown Location"

class YelpFusionAPI(PlatformAPIBase):
    """Yelp Fusion API integration"""
    
    def get_base_url(self) -> str:
        return "https://api.yelp.com/v3"
    
    def setup_authentication(self, **kwargs):
        """Setup API key authentication for Yelp"""
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        })
    
    def get_reviews(self, location_id: str, limit: int = 50, offset: int = 0) -> List[ReviewData]:
        """Fetch reviews from Yelp (Note: Yelp API has limited review access)"""
        try:
            endpoint = f"businesses/{location_id}/reviews"
            params = {'limit': min(limit, 3), 'sort_by': 'newest'}  # Yelp only returns 3 reviews
            
            response = self.make_request('GET', endpoint, params=params)
            reviews = []
            
            # Get business info for location name
            business_info = self.get_location_info(location_id)
            
            for review_data in response.get('reviews', []):
                review = ReviewData(
                    platform='yelp',
                    platform_review_id=review_data['id'],
                    reviewer_name=review_data['user']['name'],
                    reviewer_avatar=review_data['user'].get('image_url'),
                    rating=float(review_data['rating']),
                    review_text=review_data['text'],
                    review_date=datetime.fromisoformat(review_data['time_created']),
                    location_id=location_id,
                    location_name=business_info.name,
                    language='en',  # Yelp doesn't provide language info
                    verified=False  # Yelp doesn't provide verification status
                )
                reviews.append(review)
            
            return reviews
            
        except Exception as e:
            logger.error(f"Error fetching Yelp reviews: {e}")
            return []
    
    def get_location_info(self, location_id: str) -> LocationData:
        """Get Yelp business information"""
        try:
            endpoint = f"businesses/{location_id}"
            response = self.make_request('GET', endpoint)
            
            location = LocationData(
                platform='yelp',
                platform_location_id=location_id,
                name=response['name'],
                address=self._format_yelp_address(response.get('location', {})),
                phone=response.get('phone'),
                website=response.get('url'),
                category=', '.join([cat['title'] for cat in response.get('categories', [])]),
                rating=float(response.get('rating', 0)),
                review_count=int(response.get('review_count', 0)),
                photos=response.get('photos', [])[:5]
            )
            
            return location
            
        except Exception as e:
            logger.error(f"Error fetching Yelp business info: {e}")
            raise
    
    def post_response(self, review_id: str, response_text: str) -> bool:
        """Yelp doesn't support posting responses via API"""
        logger.warning("Yelp API doesn't support posting review responses")
        return False
    
    def _format_yelp_address(self, location_data: Dict) -> str:
        """Format address from Yelp location object"""
        parts = []
        if location_data.get('address1'):
            parts.append(location_data['address1'])
        if location_data.get('city'):
            parts.append(location_data['city'])
        if location_data.get('state'):
            parts.append(location_data['state'])
        if location_data.get('zip_code'):
            parts.append(location_data['zip_code'])
        return ', '.join(parts)
    
    def search_businesses(self, term: str, location: str, limit: int = 20) -> List[Dict]:
        """Search for businesses on Yelp"""
        try:
            endpoint = "businesses/search"
            params = {
                'term': term,
                'location': location,
                'limit': min(limit, 50)
            }
            
            response = self.make_request('GET', endpoint, params=params)
            return response.get('businesses', [])
            
        except Exception as e:
            logger.error(f"Error searching Yelp businesses: {e}")
            return []

class FacebookGraphAPI(PlatformAPIBase):
    """Facebook Graph API integration"""
    
    def get_base_url(self) -> str:
        return "https://graph.facebook.com/v18.0"
    
    def setup_authentication(self, **kwargs):
        """Setup access token authentication for Facebook"""
        self.access_token = self.api_key  # For Facebook, api_key is the access token
        self.session.params.update({'access_token': self.access_token})
    
    def get_reviews(self, location_id: str, limit: int = 50, offset: int = 0) -> List[ReviewData]:
        """Fetch reviews from Facebook Page"""
        try:
            endpoint = f"{location_id}/ratings"
            params = {
                'fields': 'reviewer,rating,review_text,created_time,recommendation_type',
                'limit': min(limit, 100)
            }
            
            response = self.make_request('GET', endpoint, params=params)
            reviews = []
            
            # Get page info for location name
            page_info = self.get_location_info(location_id)
            
            for review_data in response.get('data', []):
                # Facebook uses recommendation_type instead of numeric rating
                rating = 5.0 if review_data.get('recommendation_type') == 'positive' else 1.0
                
                review = ReviewData(
                    platform='facebook',
                    platform_review_id=review_data['id'],
                    reviewer_name=review_data['reviewer']['name'],
                    reviewer_avatar=f"https://graph.facebook.com/{review_data['reviewer']['id']}/picture",
                    rating=rating,
                    review_text=review_data.get('review_text', ''),
                    review_date=datetime.fromisoformat(review_data['created_time'].replace('Z', '+00:00')),
                    location_id=location_id,
                    location_name=page_info.name,
                    language='en',  # Facebook doesn't provide language info
                    verified=False
                )
                reviews.append(review)
            
            return reviews
            
        except Exception as e:
            logger.error(f"Error fetching Facebook reviews: {e}")
            return []
    
    def get_location_info(self, location_id: str) -> LocationData:
        """Get Facebook Page information"""
        try:
            endpoint = location_id
            params = {
                'fields': 'name,location,phone,website,category,overall_star_rating,rating_count,cover'
            }
            
            response = self.make_request('GET', endpoint, params=params)
            
            location = LocationData(
                platform='facebook',
                platform_location_id=location_id,
                name=response['name'],
                address=self._format_facebook_address(response.get('location', {})),
                phone=response.get('phone'),
                website=response.get('website'),
                category=response.get('category', 'Business'),
                rating=float(response.get('overall_star_rating', 0)),
                review_count=int(response.get('rating_count', 0)),
                photos=[response.get('cover', {}).get('source')] if response.get('cover') else []
            )
            
            return location
            
        except Exception as e:
            logger.error(f"Error fetching Facebook page info: {e}")
            raise
    
    def post_response(self, review_id: str, response_text: str) -> bool:
        """Facebook doesn't support posting responses to reviews via API"""
        logger.warning("Facebook API doesn't support posting review responses")
        return False
    
    def _format_facebook_address(self, location_data: Dict) -> str:
        """Format address from Facebook location object"""
        parts = []
        if location_data.get('street'):
            parts.append(location_data['street'])
        if location_data.get('city'):
            parts.append(location_data['city'])
        if location_data.get('state'):
            parts.append(location_data['state'])
        if location_data.get('zip'):
            parts.append(location_data['zip'])
        return ', '.join(parts)

class TripAdvisorAPI(PlatformAPIBase):
    """TripAdvisor API integration"""
    
    def get_base_url(self) -> str:
        return "https://api.tripadvisor.com/api/partner/2.0"
    
    def setup_authentication(self, **kwargs):
        """Setup API key authentication for TripAdvisor"""
        self.session.headers.update({
            'X-TripAdvisor-API-Key': self.api_key,
            'Content-Type': 'application/json'
        })
    
    def get_reviews(self, location_id: str, limit: int = 50, offset: int = 0) -> List[ReviewData]:
        """Fetch reviews from TripAdvisor"""
        try:
            endpoint = f"location/{location_id}/reviews"
            params = {
                'limit': min(limit, 20),  # TripAdvisor typical limit
                'offset': offset,
                'lang': 'en'
            }
            
            response = self.make_request('GET', endpoint, params=params)
            reviews = []
            
            # Get location info for location name
            location_info = self.get_location_info(location_id)
            
            for review_data in response.get('data', []):
                review = ReviewData(
                    platform='tripadvisor',
                    platform_review_id=str(review_data['id']),
                    reviewer_name=review_data['user']['username'],
                    reviewer_avatar=review_data['user'].get('avatar', {}).get('large'),
                    rating=float(review_data['rating']),
                    review_text=review_data.get('text', ''),
                    review_date=datetime.fromisoformat(review_data['published_date']),
                    location_id=location_id,
                    location_name=location_info.name,
                    language=review_data.get('lang', 'en'),
                    verified=review_data.get('is_machine_translated', False),
                    helpful_count=review_data.get('helpful_votes', 0)
                )
                reviews.append(review)
            
            return reviews
            
        except Exception as e:
            logger.error(f"Error fetching TripAdvisor reviews: {e}")
            return []
    
    def get_location_info(self, location_id: str) -> LocationData:
        """Get TripAdvisor location information"""
        try:
            endpoint = f"location/{location_id}"
            params = {'lang': 'en'}
            
            response = self.make_request('GET', endpoint, params=params)
            
            location = LocationData(
                platform='tripadvisor',
                platform_location_id=location_id,
                name=response['name'],
                address=self._format_tripadvisor_address(response.get('address_obj', {})),
                phone=response.get('phone'),
                website=response.get('website'),
                category=', '.join([cat['name'] for cat in response.get('category', {}).get('subcategory', [])]),
                rating=float(response.get('rating', 0)),
                review_count=int(response.get('num_reviews', 0)),
                photos=[photo['images']['large']['url'] for photo in response.get('photos', [])[:5]]
            )
            
            return location
            
        except Exception as e:
            logger.error(f"Error fetching TripAdvisor location info: {e}")
            raise
    
    def post_response(self, review_id: str, response_text: str) -> bool:
        """TripAdvisor doesn't support posting responses via API"""
        logger.warning("TripAdvisor API doesn't support posting review responses")
        return False
    
    def _format_tripadvisor_address(self, address_data: Dict) -> str:
        """Format address from TripAdvisor address object"""
        parts = []
        if address_data.get('street1'):
            parts.append(address_data['street1'])
        if address_data.get('city'):
            parts.append(address_data['city'])
        if address_data.get('state'):
            parts.append(address_data['state'])
        if address_data.get('postalcode'):
            parts.append(address_data['postalcode'])
        return ', '.join(parts)
    
    def search_locations(self, query: str, limit: int = 20) -> List[Dict]:
        """Search for locations on TripAdvisor"""
        try:
            endpoint = "search"
            params = {
                'query': query,
                'limit': min(limit, 20),
                'lang': 'en'
            }
            
            response = self.make_request('GET', endpoint, params=params)
            return response.get('data', [])
            
        except Exception as e:
            logger.error(f"Error searching TripAdvisor locations: {e}")
            return []

class PlatformAPIManager:
    """Manager class for all platform APIs"""
    
    def __init__(self):
        self.platforms = {}
        self.initialize_platforms()
    
    def initialize_platforms(self):
        """Initialize all platform APIs with credentials from environment"""
        # Google My Business
        gmb_key = os.getenv('GOOGLE_MY_BUSINESS_API_KEY')
        gmb_token = os.getenv('GOOGLE_MY_BUSINESS_ACCESS_TOKEN')
        if gmb_key and gmb_token:
            self.platforms['google'] = GoogleMyBusinessAPI(
                api_key=gmb_key,
                access_token=gmb_token
            )
        
        # Yelp
        yelp_key = os.getenv('YELP_API_KEY')
        if yelp_key:
            self.platforms['yelp'] = YelpFusionAPI(api_key=yelp_key)
        
        # Facebook
        fb_token = os.getenv('FACEBOOK_ACCESS_TOKEN')
        if fb_token:
            self.platforms['facebook'] = FacebookGraphAPI(api_key=fb_token)
        
        # TripAdvisor
        ta_key = os.getenv('TRIPADVISOR_API_KEY')
        if ta_key:
            self.platforms['tripadvisor'] = TripAdvisorAPI(api_key=ta_key)
    
    def get_platform(self, platform_name: str) -> Optional[PlatformAPIBase]:
        """Get platform API instance"""
        return self.platforms.get(platform_name.lower())
    
    def get_available_platforms(self) -> List[str]:
        """Get list of available platforms"""
        return list(self.platforms.keys())
    
    def sync_reviews(self, platform: str, location_id: str, limit: int = 50) -> List[ReviewData]:
        """Sync reviews from a platform"""
        api = self.get_platform(platform)
        if not api:
            logger.error(f"Platform {platform} not available")
            return []
        
        return api.get_reviews(location_id, limit)
    
    def sync_all_platforms(self, location_configs: Dict[str, str], limit: int = 50) -> Dict[str, List[ReviewData]]:
        """Sync reviews from all configured platforms"""
        results = {}
        
        for platform, location_id in location_configs.items():
            try:
                reviews = self.sync_reviews(platform, location_id, limit)
                results[platform] = reviews
                logger.info(f"Synced {len(reviews)} reviews from {platform}")
            except Exception as e:
                logger.error(f"Failed to sync reviews from {platform}: {e}")
                results[platform] = []
        
        return results
    
    def get_location_info(self, platform: str, location_id: str) -> Optional[LocationData]:
        """Get location information from a platform"""
        api = self.get_platform(platform)
        if not api:
            logger.error(f"Platform {platform} not available")
            return None
        
        try:
            return api.get_location_info(location_id)
        except Exception as e:
            logger.error(f"Failed to get location info from {platform}: {e}")
            return None
    
    def post_response(self, platform: str, review_id: str, response_text: str) -> bool:
        """Post response to a review on a platform"""
        api = self.get_platform(platform)
        if not api:
            logger.error(f"Platform {platform} not available")
            return False
        
        return api.post_response(review_id, response_text)

# Global instance
platform_manager = PlatformAPIManager()

