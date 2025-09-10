import random
import requests
from datetime import datetime
from typing import List, Dict
import json

class TrendingHashtagGenerator:
    """Generate trending hashtags and optimized metadata for YouTube Shorts"""
    
    def __init__(self):
        # Base hashtag categories
        self.hashtag_pools = {
            'viral_2025': [
                'viral', 'trending', 'fyp', 'foryou', 'foryoupage', 
                'explore', 'explorepage', 'viralvideo', 'trendingnow',
                'mustwatch', 'viralshorts', 'trendingshorts', 'fypシ'
            ],
            'time_based': [],  # Will be generated dynamically
            'engagement': [
                'subscribe', 'like', 'share', 'comment', 'follow',
                'subscribenow', 'likeandsubscribe', 'sharethis',
                'commentbelow', 'followme', 'subforsub', 'newvideo'
            ],
            'shorts_specific': [
                'shorts', 'youtubeshorts', 'shortsvideo', 'shortsfeed',
                'shortsyoutube', 'ytshorts', 'shortsviral', 'shortstiktok',
                'reels', 'shortscreator', 'shortscompetition'
            ],
            'entertainment': [
                'entertainment', 'fun', 'funny', 'comedy', 'memes',
                'lol', 'humor', 'jokes', 'laugh', 'hilarious',
                'funnyvideos', 'comedyshorts', 'meme', 'dankmemes'
            ],
            'lifestyle': [
                'lifestyle', 'life', 'daily', 'vlog', 'dayinmylife',
                'routine', 'aesthetic', 'vibes', 'mood', 'relatable',
                'lifehacks', 'tips', 'motivation', 'inspiration'
            ],
            'challenges': [
                'challenge', 'challengeaccepted', 'viral challenge',
                'trendingchallenge', 'newchallenge', 'challengevideo',
                'dare', 'trynottolaugh', 'impossible', 'epic'
            ],
            'seasonal': [],  # Will be updated based on current date
            'countries': [
                'usa', 'india', 'uk', 'canada', 'australia',
                'global', 'worldwide', 'international'
            ]
        }
        
        self.title_emojis = ['🔥', '😱', '💯', '⚡', '🎯', '✨', '🚀', '💥', '🎬', '📱']
        self.update_time_based_hashtags()
    
    def update_time_based_hashtags(self):
        """Update hashtags based on current time/season"""
        now = datetime.now()
        year = now.year
        month = now.strftime('%B').lower()
        
        # Time-based hashtags
        self.hashtag_pools['time_based'] = [
            f'{year}', f'new{year}', f'{month}{year}',
            f'trending{year}', f'viral{year}', f'best{year}',
            f'{month}vibes', 'todaytrending', 'dailycontent'
        ]
        
        # Seasonal hashtags
        seasons = {
            (12, 1, 2): ['winter', 'wintervibes', 'cold', 'snow', 'cozy'],
            (3, 4, 5): ['spring', 'springvibes', 'flowers', 'fresh', 'bloom'],
            (6, 7, 8): ['summer', 'summervibes', 'sunny', 'hot', 'vacation'],
            (9, 10, 11): ['fall', 'autumn', 'fallvibes', 'cozy', 'halloween']
        }
        
        current_month = now.month
        for months, tags in seasons.items():
            if current_month in months:
                self.hashtag_pools['seasonal'] = tags
                break
    
    def get_trending_from_api(self) -> List[str]:
        """
        Attempt to get trending topics from various sources
        Note: Most require API keys, this is a template
        """
        trending = []
        
            # Example: RapidAPI trending hashtags (requires API key)
            # Uncomment and add your API key to use
        """
        try:
            url = "https://hashtagy-generate-hashtags.p.rapidapi.com/v1/trending"
            headers = {
                "X-RapidAPI-Key": "YOUR_RAPIDAPI_KEY",
                "X-RapidAPI-Host": "hashtagy-generate-hashtags.p.rapidapi.com"
            }
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                trending = data.get('tags', [])[:10]
        except:
            pass
        """
        
        # Fallback trending topics (updated regularly in production)
        fallback_trending = [
            'asmr', 'satisfying', 'oddlysatisfying', 'relaxing',
            'diy', 'howto', 'tutorial', 'learnontiktok',
            'beforeandafter', 'transformation', 'makeover',
            'foodie', 'recipe', 'cooking', 'yummy',
            'workout', 'fitness', 'gym', 'health',
            'tech', 'gadgets', 'smartphone', 'ai',
            'travel', 'wanderlust', 'adventure', 'nature'
        ]
        
        return trending if trending else random.sample(fallback_trending, 5)
    
    def generate_hashtags(self, video_title: str = "", category: str = None, count: int = 30) -> List[str]:
        """Generate optimized hashtags for maximum reach"""
        hashtags = []
        
        # Core viral hashtags (always include)
        hashtags.extend(random.sample(self.hashtag_pools['viral_2025'], 5))
        
        # Shorts specific
        hashtags.extend(random.sample(self.hashtag_pools['shorts_specific'], 4))
        
        # Time-based hashtags
        hashtags.extend(random.sample(self.hashtag_pools['time_based'], 3))
        
        # Seasonal if available
        if self.hashtag_pools.get('seasonal'):
            hashtags.extend(random.sample(self.hashtag_pools['seasonal'], 2))
        
        # Category specific
        if category and category in self.hashtag_pools:
            hashtags.extend(random.sample(self.hashtag_pools[category], 3))
        
        # Engagement hashtags
        hashtags.extend(random.sample(self.hashtag_pools['engagement'], 2))
        
        # Trending from API
        hashtags.extend(self.get_trending_from_api())
        
        # Title-based hashtags (extract words from title)
        if video_title:
            title_words = video_title.lower().split()
            for word in title_words[:3]:
                if len(word) > 3 and word.isalnum():
                    hashtags.append(word)
        
        # Remove duplicates and limit
        hashtags = list(dict.fromkeys(hashtags))[:count]
        
        # Format with # symbol
        return [f'#{tag.replace(" ", "")}' for tag in hashtags]
    
    def generate_viral_title(self, original_title: str) -> str:
        """Generate viral-optimized title with emojis"""
        templates = [
            "{emoji} {title} | MUST WATCH! {emoji}",
            "{emoji} {title} - YOU WON'T BELIEVE THIS!",
            "{title} {emoji} SHOCKING RESULTS!",
            "{emoji} {title} | GONE WRONG! {emoji}",
            "{title} - WAIT FOR IT... {emoji}",
            "{emoji} {title} | 99% FAIL THIS!",
            "POV: {title} {emoji} VIRAL",
            "{title} {emoji} *EMOTIONAL*",
            "{emoji} IMPOSSIBLE {title} CHALLENGE!",
            "{title} IN 60 SECONDS! {emoji}"
        ]
        
        # Clean title
        clean_title = original_title[:50] if len(original_title) > 50 else original_title
        
        # Select random template and emojis
        template = random.choice(templates)
        emoji = random.choice(self.title_emojis)
        
        # Format title
        viral_title = template.format(title=clean_title.upper(), emoji=emoji)
        
        # Ensure it's under YouTube's 100 character limit
        if len(viral_title) > 100:
            viral_title = viral_title[:97] + "..."
        
        return viral_title
    
    def generate_description(self, title: str, hashtags: List[str]) -> str:
        """Generate SEO-optimized description"""
        description = f"""
{title}

🔔 SUBSCRIBE & TURN ON NOTIFICATIONS for daily uploads!
👍 LIKE this video if you enjoyed!
💬 COMMENT your thoughts below!
📤 SHARE with your friends!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 In This Video:
Watch till the end for a surprise! This viral short will blow your mind!
Don't forget to watch our other trending videos!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏷️ Trending Hashtags:
{' '.join(hashtags)} #cdrama #kdrama #drama #chinesedrama #kpop
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📱 Follow Us:
Instagram: @C-Drama-02
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎬 Upload Schedule: UPLOAD EVERY HOUR!
🔥 New Shorts Every Hour!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Search Terms:
viral shorts, youtube shorts, trending {datetime.now().year}, funny videos, 
best shorts, must watch, viral videos, {' '.join([h.replace('#', '') for h in hashtags[15:25]])}

#Shorts {' '.join(hashtags[25:])}

"""
        return description.strip()
    
    def get_best_upload_times(self) -> Dict[str, List[str]]:
        """Get best upload times for different time zones"""
        return {
            'EST': ['6:00', '12:00', '17:00', '20:00'],
            'PST': ['7:00', '12:00', '16:00', '21:00'],
            'GMT': ['8:00', '13:00', '18:00', '22:00'],
            'IST': ['9:00', '14:00', '19:00', '23:00']
        }
    
    def analyze_title_for_category(self, title: str) -> str:
        """Analyze title to determine best category"""
        title_lower = title.lower()
        
        category_keywords = {
            'entertainment': ['funny', 'comedy', 'laugh', 'meme', 'prank', 'fail'],
            'lifestyle': ['routine', 'day', 'life', 'vlog', 'morning', 'night'],
            'challenges': ['challenge', 'try', 'impossible', 'dare', '24 hours'],
            'gaming': ['game', 'gaming', 'play', 'minecraft', 'fortnite', 'roblox'],
            'tech': ['phone', 'app', 'gadget', 'tech', 'review', 'unboxing'],
            'food': ['food', 'recipe', 'cooking', 'eating', 'restaurant', 'taste']
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in title_lower for keyword in keywords):
                return category
        
        return 'entertainment'  # default category

# Example usage function
def test_generator():
    """Test the hashtag generator"""
    generator = TrendingHashtagGenerator()
    
    # Test with a sample title
    original_title = "Amazing Life Hack"
    
    # Generate viral title
    viral_title = generator.generate_viral_title(original_title)
    print(f"Viral Title: {viral_title}\n")
    
    # Analyze category
    category = generator.analyze_title_for_category(original_title)
    print(f"Detected Category: {category}\n")
    
    # Generate hashtags
    hashtags = generator.generate_hashtags(original_title, category)
    print(f"Generated {len(hashtags)} Hashtags:")
    print(' '.join(hashtags[:10]))
    
    # Generate description
    description = generator.generate_description(viral_title, hashtags)
    print(f"Description Preview (first 200 chars):")
    print(description[:200] + "...")

if __name__ == "__main__":
    test_generator()