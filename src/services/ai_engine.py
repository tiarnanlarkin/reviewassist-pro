"""
Advanced AI Engine for ReviewAssist Pro
Provides intelligent review analysis, response generation, and predictive insights
"""

import openai
import json
import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import statistics
from collections import defaultdict, Counter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResponseTone(Enum):
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    APOLOGETIC = "apologetic"
    GRATEFUL = "grateful"
    EMPATHETIC = "empathetic"
    ENTHUSIASTIC = "enthusiastic"

class BusinessType(Enum):
    RESTAURANT = "restaurant"
    HOTEL = "hotel"
    RETAIL = "retail"
    SERVICE = "service"
    HEALTHCARE = "healthcare"
    AUTOMOTIVE = "automotive"
    BEAUTY = "beauty"
    FITNESS = "fitness"

class EmotionType(Enum):
    DELIGHTED = "delighted"
    SATISFIED = "satisfied"
    NEUTRAL = "neutral"
    DISAPPOINTED = "disappointed"
    FRUSTRATED = "frustrated"
    ANGRY = "angry"
    CONCERNED = "concerned"
    EXCITED = "excited"

class ReviewAspect(Enum):
    SERVICE = "service"
    QUALITY = "quality"
    PRICE = "price"
    CLEANLINESS = "cleanliness"
    ATMOSPHERE = "atmosphere"
    STAFF = "staff"
    LOCATION = "location"
    SPEED = "speed"
    VALUE = "value"

@dataclass
class SentimentAnalysis:
    overall_sentiment: float  # -1 to 1
    confidence: float  # 0 to 1
    emotion: EmotionType
    aspects: Dict[ReviewAspect, float]
    keywords: List[str]
    urgency_score: float  # 0 to 1

@dataclass
class ReviewCategory:
    primary_category: str
    secondary_categories: List[str]
    priority_score: float  # 0 to 1
    department: str
    tags: List[str]

@dataclass
class SmartResponse:
    response_text: str
    tone: ResponseTone
    confidence: float
    personalization_elements: List[str]
    suggested_actions: List[str]
    quality_score: float

@dataclass
class CompetitorInsight:
    competitor_name: str
    sentiment_comparison: float
    volume_comparison: float
    strengths: List[str]
    weaknesses: List[str]
    opportunities: List[str]

@dataclass
class PredictiveInsight:
    prediction_type: str
    forecast_value: float
    confidence: float
    time_horizon: str
    contributing_factors: List[str]
    recommended_actions: List[str]

class AIEngine:
    """Advanced AI Engine for intelligent review management"""
    
    def __init__(self):
        self.openai_client = openai
        self.response_templates = self._load_response_templates()
        self.sentiment_cache = {}
        self.category_cache = {}
        
    def _load_response_templates(self) -> Dict[str, Dict[str, str]]:
        """Load response templates for different business types and tones"""
        return {
            BusinessType.RESTAURANT.value: {
                ResponseTone.PROFESSIONAL.value: "Thank you for your feedback about your dining experience at {business_name}. We appreciate you taking the time to share your thoughts.",
                ResponseTone.FRIENDLY.value: "Hi {customer_name}! Thanks so much for visiting {business_name} and sharing your experience with us!",
                ResponseTone.APOLOGETIC.value: "We sincerely apologize for the experience you had at {business_name}. Your feedback is invaluable to us.",
                ResponseTone.GRATEFUL.value: "We're so grateful for your wonderful review! It means the world to our team at {business_name}.",
            },
            BusinessType.HOTEL.value: {
                ResponseTone.PROFESSIONAL.value: "Thank you for choosing {business_name} for your stay and for sharing your feedback.",
                ResponseTone.FRIENDLY.value: "Hello {customer_name}! We're delighted you stayed with us at {business_name}!",
                ResponseTone.APOLOGETIC.value: "We deeply regret that your stay at {business_name} did not meet your expectations.",
                ResponseTone.GRATEFUL.value: "Thank you for the fantastic review! We're thrilled you enjoyed your stay at {business_name}.",
            },
            BusinessType.RETAIL.value: {
                ResponseTone.PROFESSIONAL.value: "Thank you for shopping with {business_name} and for taking the time to leave a review.",
                ResponseTone.FRIENDLY.value: "Hey {customer_name}! Thanks for being an awesome customer at {business_name}!",
                ResponseTone.APOLOGETIC.value: "We apologize for any inconvenience during your shopping experience at {business_name}.",
                ResponseTone.GRATEFUL.value: "We're so happy you had a great shopping experience at {business_name}!",
            }
        }

    async def analyze_sentiment(self, review_text: str, business_type: str = None) -> SentimentAnalysis:
        """Advanced sentiment analysis with emotion detection and aspect analysis"""
        try:
            # Check cache first
            cache_key = f"{hash(review_text)}_{business_type}"
            if cache_key in self.sentiment_cache:
                return self.sentiment_cache[cache_key]

            prompt = f"""
            Analyze the following review with advanced sentiment analysis:
            
            Review: "{review_text}"
            Business Type: {business_type or 'general'}
            
            Provide a detailed analysis in JSON format:
            {{
                "overall_sentiment": <float between -1 and 1>,
                "confidence": <float between 0 and 1>,
                "emotion": "<one of: delighted, satisfied, neutral, disappointed, frustrated, angry, concerned, excited>",
                "aspects": {{
                    "service": <sentiment score -1 to 1>,
                    "quality": <sentiment score -1 to 1>,
                    "price": <sentiment score -1 to 1>,
                    "cleanliness": <sentiment score -1 to 1>,
                    "atmosphere": <sentiment score -1 to 1>,
                    "staff": <sentiment score -1 to 1>,
                    "location": <sentiment score -1 to 1>,
                    "speed": <sentiment score -1 to 1>,
                    "value": <sentiment score -1 to 1>
                }},
                "keywords": ["list", "of", "important", "keywords"],
                "urgency_score": <float between 0 and 1>
            }}
            
            Only include aspects that are mentioned in the review. Set urgency_score high (0.7+) for complaints requiring immediate attention.
            """

            response = await self.openai_client.ChatCompletion.acreate(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )

            analysis_data = json.loads(response.choices[0].message.content)
            
            # Convert to SentimentAnalysis object
            aspects = {ReviewAspect(k): v for k, v in analysis_data.get("aspects", {}).items() 
                      if k in [aspect.value for aspect in ReviewAspect]}
            
            sentiment_analysis = SentimentAnalysis(
                overall_sentiment=analysis_data["overall_sentiment"],
                confidence=analysis_data["confidence"],
                emotion=EmotionType(analysis_data["emotion"]),
                aspects=aspects,
                keywords=analysis_data["keywords"],
                urgency_score=analysis_data["urgency_score"]
            )
            
            # Cache the result
            self.sentiment_cache[cache_key] = sentiment_analysis
            return sentiment_analysis
            
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {e}")
            # Return default analysis
            return SentimentAnalysis(
                overall_sentiment=0.0,
                confidence=0.5,
                emotion=EmotionType.NEUTRAL,
                aspects={},
                keywords=[],
                urgency_score=0.5
            )

    async def categorize_review(self, review_text: str, business_type: str = None) -> ReviewCategory:
        """Intelligent review categorization with priority scoring"""
        try:
            cache_key = f"cat_{hash(review_text)}_{business_type}"
            if cache_key in self.category_cache:
                return self.category_cache[cache_key]

            prompt = f"""
            Categorize the following review intelligently:
            
            Review: "{review_text}"
            Business Type: {business_type or 'general'}
            
            Provide categorization in JSON format:
            {{
                "primary_category": "<main category like 'complaint', 'compliment', 'suggestion', 'question', 'general'>",
                "secondary_categories": ["list", "of", "secondary", "categories"],
                "priority_score": <float between 0 and 1, where 1 is highest priority>,
                "department": "<which department should handle this: 'management', 'customer_service', 'operations', 'marketing'>",
                "tags": ["relevant", "tags", "for", "filtering"]
            }}
            
            Priority score should be high (0.7+) for urgent complaints, medium (0.4-0.7) for general feedback, low (0.0-0.4) for compliments.
            """

            response = await self.openai_client.ChatCompletion.acreate(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )

            category_data = json.loads(response.choices[0].message.content)
            
            category = ReviewCategory(
                primary_category=category_data["primary_category"],
                secondary_categories=category_data["secondary_categories"],
                priority_score=category_data["priority_score"],
                department=category_data["department"],
                tags=category_data["tags"]
            )
            
            self.category_cache[cache_key] = category
            return category
            
        except Exception as e:
            logger.error(f"Error in review categorization: {e}")
            return ReviewCategory(
                primary_category="general",
                secondary_categories=[],
                priority_score=0.5,
                department="customer_service",
                tags=[]
            )

    async def generate_smart_response(
        self, 
        review_text: str, 
        sentiment: SentimentAnalysis,
        business_name: str,
        business_type: str = None,
        tone: ResponseTone = ResponseTone.PROFESSIONAL,
        customer_name: str = None
    ) -> SmartResponse:
        """Generate intelligent, context-aware responses"""
        try:
            # Determine appropriate tone based on sentiment if not specified
            if sentiment.overall_sentiment < -0.5:
                suggested_tone = ResponseTone.APOLOGETIC
            elif sentiment.overall_sentiment > 0.5:
                suggested_tone = ResponseTone.GRATEFUL
            else:
                suggested_tone = tone

            # Get base template
            base_template = self.response_templates.get(
                business_type, 
                self.response_templates[BusinessType.RESTAURANT.value]
            ).get(suggested_tone.value, "Thank you for your feedback.")

            prompt = f"""
            Generate a personalized, intelligent response to this review:
            
            Review: "{review_text}"
            Business: {business_name}
            Business Type: {business_type or 'general'}
            Customer Name: {customer_name or 'Valued Customer'}
            Sentiment Score: {sentiment.overall_sentiment}
            Emotion: {sentiment.emotion.value}
            Key Aspects: {list(sentiment.aspects.keys())}
            Urgency: {sentiment.urgency_score}
            Desired Tone: {suggested_tone.value}
            
            Base Template: "{base_template}"
            
            Create a response that:
            1. Addresses specific points mentioned in the review
            2. Matches the desired tone
            3. Includes personalization elements
            4. Suggests concrete actions if needed
            5. Is professional yet human
            
            Provide response in JSON format:
            {{
                "response_text": "<the complete response>",
                "personalization_elements": ["elements", "that", "make", "it", "personal"],
                "suggested_actions": ["concrete", "actions", "to", "take"],
                "quality_score": <float between 0 and 1>
            }}
            """

            response = await self.openai_client.ChatCompletion.acreate(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )

            response_data = json.loads(response.choices[0].message.content)
            
            return SmartResponse(
                response_text=response_data["response_text"],
                tone=suggested_tone,
                confidence=sentiment.confidence,
                personalization_elements=response_data["personalization_elements"],
                suggested_actions=response_data["suggested_actions"],
                quality_score=response_data["quality_score"]
            )
            
        except Exception as e:
            logger.error(f"Error generating smart response: {e}")
            return SmartResponse(
                response_text="Thank you for your feedback. We appreciate you taking the time to share your experience with us.",
                tone=tone,
                confidence=0.5,
                personalization_elements=[],
                suggested_actions=[],
                quality_score=0.5
            )

    async def analyze_competitors(self, reviews_data: List[Dict], competitor_data: List[Dict]) -> List[CompetitorInsight]:
        """Analyze competitor performance and identify opportunities"""
        try:
            insights = []
            
            for competitor in competitor_data:
                competitor_reviews = competitor.get('reviews', [])
                
                # Calculate sentiment comparison
                our_sentiment = statistics.mean([r.get('sentiment', 0) for r in reviews_data])
                competitor_sentiment = statistics.mean([r.get('sentiment', 0) for r in competitor_reviews])
                sentiment_comparison = our_sentiment - competitor_sentiment
                
                # Calculate volume comparison
                our_volume = len(reviews_data)
                competitor_volume = len(competitor_reviews)
                volume_comparison = our_volume / max(competitor_volume, 1)
                
                prompt = f"""
                Analyze competitor performance and identify insights:
                
                Our Business:
                - Average Sentiment: {our_sentiment:.2f}
                - Review Volume: {our_volume}
                - Recent Reviews: {reviews_data[-5:] if reviews_data else []}
                
                Competitor: {competitor.get('name', 'Unknown')}
                - Average Sentiment: {competitor_sentiment:.2f}
                - Review Volume: {competitor_volume}
                - Recent Reviews: {competitor_reviews[-5:] if competitor_reviews else []}
                
                Provide analysis in JSON format:
                {{
                    "strengths": ["competitor's", "key", "strengths"],
                    "weaknesses": ["competitor's", "weaknesses"],
                    "opportunities": ["opportunities", "for", "us", "to", "improve"]
                }}
                """

                response = await self.openai_client.ChatCompletion.acreate(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2
                )

                analysis_data = json.loads(response.choices[0].message.content)
                
                insight = CompetitorInsight(
                    competitor_name=competitor.get('name', 'Unknown'),
                    sentiment_comparison=sentiment_comparison,
                    volume_comparison=volume_comparison,
                    strengths=analysis_data["strengths"],
                    weaknesses=analysis_data["weaknesses"],
                    opportunities=analysis_data["opportunities"]
                )
                
                insights.append(insight)
            
            return insights
            
        except Exception as e:
            logger.error(f"Error in competitor analysis: {e}")
            return []

    async def generate_predictive_insights(self, historical_data: List[Dict]) -> List[PredictiveInsight]:
        """Generate predictive insights and forecasts"""
        try:
            insights = []
            
            if len(historical_data) < 10:
                return insights  # Need sufficient data for predictions
            
            # Analyze trends
            recent_data = historical_data[-30:]  # Last 30 data points
            older_data = historical_data[-60:-30]  # Previous 30 data points
            
            # Sentiment trend
            recent_sentiment = statistics.mean([d.get('sentiment', 0) for d in recent_data])
            older_sentiment = statistics.mean([d.get('sentiment', 0) for d in older_data])
            sentiment_trend = recent_sentiment - older_sentiment
            
            # Volume trend
            recent_volume = len(recent_data)
            older_volume = len(older_data)
            volume_trend = (recent_volume - older_volume) / max(older_volume, 1)
            
            prompt = f"""
            Generate predictive insights based on historical review data:
            
            Data Summary:
            - Total Reviews: {len(historical_data)}
            - Recent Sentiment Trend: {sentiment_trend:.3f}
            - Volume Trend: {volume_trend:.3f}
            - Recent Average Sentiment: {recent_sentiment:.2f}
            - Recent Volume: {recent_volume}
            
            Generate 3-5 predictive insights in JSON format:
            {{
                "insights": [
                    {{
                        "prediction_type": "<type like 'sentiment_forecast', 'volume_prediction', 'risk_assessment'>",
                        "forecast_value": <predicted value>,
                        "confidence": <confidence 0-1>,
                        "time_horizon": "<time period like '30_days', '90_days'>",
                        "contributing_factors": ["factors", "influencing", "prediction"],
                        "recommended_actions": ["actions", "to", "take"]
                    }}
                ]
            }}
            """

            response = await self.openai_client.ChatCompletion.acreate(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )

            insights_data = json.loads(response.choices[0].message.content)
            
            for insight_data in insights_data["insights"]:
                insight = PredictiveInsight(
                    prediction_type=insight_data["prediction_type"],
                    forecast_value=insight_data["forecast_value"],
                    confidence=insight_data["confidence"],
                    time_horizon=insight_data["time_horizon"],
                    contributing_factors=insight_data["contributing_factors"],
                    recommended_actions=insight_data["recommended_actions"]
                )
                insights.append(insight)
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating predictive insights: {e}")
            return []

    def detect_review_patterns(self, reviews: List[Dict]) -> Dict[str, Any]:
        """Detect patterns and anomalies in review data"""
        try:
            patterns = {
                "sentiment_patterns": {},
                "temporal_patterns": {},
                "keyword_patterns": {},
                "anomalies": []
            }
            
            # Sentiment patterns
            sentiments = [r.get('sentiment', 0) for r in reviews]
            patterns["sentiment_patterns"] = {
                "average": statistics.mean(sentiments),
                "std_dev": statistics.stdev(sentiments) if len(sentiments) > 1 else 0,
                "trend": "improving" if len(sentiments) > 5 and sentiments[-5:] > sentiments[-10:-5] else "stable"
            }
            
            # Temporal patterns
            review_dates = [r.get('date') for r in reviews if r.get('date')]
            if review_dates:
                # Group by day of week, hour, etc.
                patterns["temporal_patterns"] = {
                    "peak_days": "weekends",  # Simplified
                    "peak_hours": "evening",  # Simplified
                    "seasonal_trend": "stable"  # Simplified
                }
            
            # Keyword patterns
            all_keywords = []
            for review in reviews:
                keywords = review.get('keywords', [])
                all_keywords.extend(keywords)
            
            keyword_counts = Counter(all_keywords)
            patterns["keyword_patterns"] = {
                "top_keywords": keyword_counts.most_common(10),
                "emerging_keywords": keyword_counts.most_common(20)[10:],
                "trending_topics": ["service", "quality", "value"]  # Simplified
            }
            
            # Anomaly detection (simplified)
            recent_sentiment = statistics.mean(sentiments[-10:]) if len(sentiments) >= 10 else 0
            overall_sentiment = statistics.mean(sentiments)
            
            if abs(recent_sentiment - overall_sentiment) > 0.3:
                patterns["anomalies"].append({
                    "type": "sentiment_shift",
                    "description": f"Recent sentiment shift detected: {recent_sentiment:.2f} vs {overall_sentiment:.2f}",
                    "severity": "medium"
                })
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error detecting patterns: {e}")
            return {}

    async def generate_business_insights(self, reviews: List[Dict], business_data: Dict) -> Dict[str, Any]:
        """Generate comprehensive business insights from review data"""
        try:
            prompt = f"""
            Generate comprehensive business insights from review analysis:
            
            Business Data: {json.dumps(business_data, indent=2)}
            Review Summary:
            - Total Reviews: {len(reviews)}
            - Average Sentiment: {statistics.mean([r.get('sentiment', 0) for r in reviews]):.2f}
            - Recent Reviews: {reviews[-5:] if reviews else []}
            
            Provide insights in JSON format:
            {{
                "key_insights": ["insight1", "insight2", "insight3"],
                "improvement_opportunities": ["opportunity1", "opportunity2"],
                "competitive_advantages": ["advantage1", "advantage2"],
                "risk_factors": ["risk1", "risk2"],
                "recommended_actions": [
                    {{
                        "action": "action description",
                        "priority": "high|medium|low",
                        "timeline": "immediate|short_term|long_term",
                        "expected_impact": "impact description"
                    }}
                ]
            }}
            """

            response = await self.openai_client.ChatCompletion.acreate(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )

            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Error generating business insights: {e}")
            return {}

# Global AI engine instance
ai_engine = AIEngine()

