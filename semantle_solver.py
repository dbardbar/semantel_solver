import requests
import json
import re
import time
import sys
import random
from urllib.parse import quote, urlencode
from typing import TypedDict
from bs4 import BeautifulSoup

# Unicode Right-to-Left Mark for proper Hebrew display
RTL_MARK = '\u200F'

class GuessResult(TypedDict):
    word: str
    similarity: float
    distance: float

class SemantleSolver:
    def __init__(self, api_url="https://semantle.ishefi.com/api/distance"):
        self.api_url = api_url
        self.guess_history: list[GuessResult] = []
        self.tried_words: set[str] = set()  # Track words already tried
        self.hebrew_corpus: list[str] = []  # Hebrew word corpus for random guesses
        self.corpus_loaded = False
        self.wiktionary_cache: dict[str, list[str]] = {}
        self.seed_word = ""
    
    def load_hebrew_corpus(self) -> None:
        """Load Hebrew word corpus from online source or local file"""
        if self.corpus_loaded:
            return
        
        print("Loading Hebrew word corpus...")
        
        word_files = [ "wordlist.txt" ]
                
        # Also include a basic list of common Hebrew words as fallback
        common_hebrew_words = [
            "שלום", "אהבה", "בית", "אדם", "יום", "לילה", "מים", "ארץ", "שמש", "ירח",
            "ספר", "עיר", "דרך", "חיים", "מוות", "אוכל", "מים", "אש", "רוח", "אבן",
            "זהב", "כסף", "ברזל", "עץ", "אבן", "חול", "שמיים", "ים", "נהר", "יער",
            "פרח", "עלה", "שורש", "ענף", "פרי", "זרע", "חיה", "ציפור", "דג", "נחש",
            "כלב", "חתול", "סוס", "פרה", "כבש", "עז", "חזיר", "תרנגול", "ברווז", "דבורה",
            "אב", "אם", "בן", "בת", "אח", "אחות", "סבא", "סבתא", "דוד", "דודה",
            "יד", "רגל", "ראש", "עין", "אוזן", "אף", "פה", "שיניים", "לשון", "צוואר",
            "לב", "ריאה", "כבד", "כליה", "מוח", "עצם", "שריר", "עור", "שיער", "ציפורן",
            "לחם", "מים", "יין", "בשר", "דג", "ביצה", "חלב", "גבינה", "חמאה", "שמן",
            "מלח", "סוכר", "דבש", "פירות", "ירקות", "תבואה", "אורז", "חיטה", "שעורה", "שיפון",
            "בוקר", "צהריים", "ערב", "לילה", "שבוע", "חודש", "שנה", "זמן", "עבר", "הווה",
            "עתיד", "היום", "אתמול", "מחר", "השבוע", "החודש", "השנה", "אביב", "קיץ", "סתיו",
            "חורף", "חם", "קר", "חמים", "קריר", "גשום", "יבש", "רטוב", "יבש", "מעונן",
            "בהיר", "אפל", "אור", "חושך", "צבע", "אדום", "כחול", "ירוק", "צהוב", "שחור",
            "לבן", "אפור", "חום", "ורוד", "סגול", "כתום", "מספר", "אחד", "שניים", "שלושה",
            "ארבעה", "חמישה", "שישה", "שבעה", "שמונה", "תשעה", "עשרה", "עשרים", "מאה", "אלף",
            "גדול", "קטן", "גבוה", "נמוך", "רחב", "צר", "עבה", "דק", "כבד", "קל",
            "מהיר", "איטי", "חדש", "ישן", "טוב", "רע", "יפה", "מכוער", "חכם", "טיפש",
            "חזק", "חלש", "בריא", "חולה", "עשיר", "עני", "שמח", "עצוב", "צוחק", "בוכה",
            "אוכל", "שותה", "ישן", "ער", "הולך", "רץ", "עומד", "יושב", "שוכב", "קם",
            "רואה", "שומע", "מריח", "טועם", "נוגע", "חושב", "יודע", "זוכר", "שוכח", "לומד",
            "מלמד", "קורא", "כותב", "מצייר", "מנגן", "שרה", "רוקד", "משחק", "עובד", "נח",
            "בונה", "הורס", "פותח", "סוגר", "נותן", "לוקח", "מביא", "מוביל", "שולח", "מקבל",
            "קונה", "מוכר", "שלם", "מקבל", "מתחיל", "מסיים", "מתחיל", "עוצר", "ממשיך", "עוזב"
        ]
        
        words_set = set()

        for word_file in word_files:
            try:
                with open(word_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        word = line.strip()
                        if word and self.is_hebrew(word) and len(word) >= 2:
                            words_set.add(word)
            except Exception as e:
                continue
            print(f"Loaded {len(words_set)} words from {word_file}")
            break

        # Add common words as fallback
        for word in common_hebrew_words:
            if self.is_hebrew(word) and len(word) >= 2:
                words_set.add(word)
        
        self.hebrew_corpus = list(words_set)
        self.corpus_loaded = True
        print(f"Hebrew corpus loaded: {len(self.hebrew_corpus)} words available")
    
    def get_random_words_from_corpus(self, count: int =5) -> list[str]:
        """Get random words from Hebrew corpus, excluding already tried words"""
        if not self.corpus_loaded:
            self.load_hebrew_corpus()
        
        # Filter out already tried words
        available_words = [w for w in self.hebrew_corpus if w not in self.tried_words]
        
        if not available_words:
            return []
        
        # Return random sample
        sample_size = min(count, len(available_words))
        return random.sample(available_words, sample_size)
    
    def get_random_word(self) -> str:
        """Get a random seed word from the corpus for autonomous solving"""
        if not self.corpus_loaded:
            self.load_hebrew_corpus()
        return random.choice(self.hebrew_corpus)
    
    def submit_guess(self, word: str, sleep_time: float = 5) -> GuessResult | None:
        """
        Submit a Hebrew word guess to the API
        
        Args:
            word: Hebrew word string to guess
            
        Returns:
            dict: Response from the API containing similarity, distance, etc.
            None: If word not found or error occurred
        """
        # Check if already tried
        if word in self.tried_words:
            return None
        
        # URL encode the Hebrew word
        encoded_word = quote(word)
        url = f"{self.api_url}?word={encoded_word}"
        
        try:
            response = requests.get(url)

            if response.status_code == 429:
                print(f"Rate limit exceeded for word: {self.format_hebrew(word)}")
                time.sleep(sleep_time)
                return self.submit_guess(word, sleep_time*1.5)

            self.tried_words.add(word)

            # Handle 400 status code (word not found)
            if response.status_code == 400:
                error_text = response.text
                if "Word not found" in error_text:
                    # print(f"Word not found in game dictionary: {self.format_hebrew(word)}")

                    result: GuessResult = {
                        "word": word,
                        "similarity": -100.0,
                        "distance": -100.0,
                    }
                    self.guess_history.append(result)
                    return result
                    # return None
                else:
                    # Other 400 error
                    print(f"API error (400): {error_text}")
                    return None
            
            # Raise for other HTTP errors
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, list) and data:
               raw = data[0]
               result: GuessResult = {
                   "word": word,
                   "similarity": float(raw.get("similarity", 0.0)),
                   "distance": float(raw.get("distance", 0.0)),
               }
               self.guess_history.append(result)
               return result

            return None
                
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error making API request: {e}")
            self.tried_words.add(word)
            return None
        except requests.exceptions.RequestException as e:
            print(f"Error making API request: {e}")
            return None
    
    def is_hebrew(self, text: str) -> bool:
        if not text:
            return False
        return all('\u0590' <= char <= '\u05FF' for char in str(text))
    
    def normalize_hebrew_input(self, text: str) -> str:
        """Normalize Hebrew input from terminal - reverse if needed for correct logical order"""
        if not text or not self.is_hebrew(text):
            return text
        return text[::-1]
    
    def format_hebrew(self, text: str) -> str:
        """Format Hebrew text for proper display in terminal"""
        if not text or text == 'N/A':
            return str(text)
        
        text_str = str(text)
        if self.is_hebrew(text_str):
            return text_str[::-1]
        return text_str
    
    def display_result(self, result: GuessResult) -> None:
        """Display a formatted result from the API"""
        if result is None:
            print("No result to display")
            return
        
        word = result['word']
        formatted_word = self.format_hebrew(word)

        print(
            f"{formatted_word:<15} | "
            f"Similarity: {result['similarity']:8.1f} | "
            f"Distance: {result['distance']:8.1f} | "
            f"Guess #: {len(self.tried_words):3d}"
        )
        
        # print(f"Word: {formatted_word}", end=" ")
        # print(f"Similarity: {result['similarity']}", end=" ")
        # print(f"Distance: {result['distance']}", end=" ")
        # print(f"Guess Number: {len(self.tried_words)}")
    
    def get_top_matches(self, n: int = 10) -> list[GuessResult]:
        """Get top N matches by similarity"""
        if not self.guess_history:
            return []
        
        # Sort by similarity (highest first)
        sorted_history = sorted(self.guess_history, 
                               key=lambda x: x['similarity'], 
                               reverse=True)
        return sorted_history[:n]
    
    def show_top_matches(self, n: int = 10) -> None:
        """Display top N matches"""
        top_matches = self.get_top_matches(n)
        if not top_matches:
            print("No guesses made yet.")
            return
        
        print("\n" + "="*60)
        print(f"TOP {len(top_matches)} BEST MATCHES")
        print("="*60)
        for i, guess in enumerate(top_matches, 1):
            word = guess['word']
            formatted_word = self.format_hebrew(word)
            similarity = guess['similarity']
            distance = guess['distance']
            print(f"{i:2}. {formatted_word:25} "
                  f"Similarity: {similarity:8} "
                  f"Distance: {distance}")
        print("="*60 + "\n")
    

    def extract_words_from_wikitext_phrase(self, base_word: str, phrase, related_words, max_words: int):
        phrase = phrase.replace('(', '').replace(')', '').strip()

        for word in phrase.split():
            if (len(phrase) < 2 or not self.is_hebrew(phrase) or word == base_word or word in self.tried_words or word in related_words):
                continue
            related_words.append(word)

            if len(related_words) >= max_words:
                break


    def get_cached_related_words(self, word: str, max_words: int =30):
        """Get related words from cache if available"""
        if word in self.wiktionary_cache:
             return self.wiktionary_cache[word]

        related_words = self.get_related_words_from_wiktionary(word, max_words)
        self.wiktionary_cache[word] = related_words
        return related_words

    def get_related_words_from_wiktionary(self, word: str, max_words: int):
        """
        Fetch related words from Wiktionary Hebrew page using MediaWiki API
        
        Args:
            word: Hebrew word to look up
            max_words: Maximum number of related words to return
            
        Returns:
            list: List of related Hebrew words
        """
        
        print(f"\n[DEBUG] Wiktionary lookup for word: {self.format_hebrew(word)} (raw: {word}) max_word {max_words}")
        
        # Use MediaWiki Action API for Hebrew Wiktionary
        api_url = "https://he.wikipedia.org/w/api.php"
        
        # Headers to avoid 403 errors
        headers = {
            'User-Agent': 'SemantleSolver/1.0 (https://github.com/yourusername/semantle-solver)'
        }
        
        # MediaWiki API parameters
        params = {
            'action': 'query',
            'titles': word,
            'prop': 'revisions',
            'rvprop': 'content',
            'format': 'json',
            'formatversion': '2'
        }
        
        print(f"[DEBUG] Full request URL: {api_url}?{urlencode(params)}")
        
        try:
            response = requests.get(api_url, params=params, headers=headers, timeout=10)
            # print(f"[DEBUG] Response status code: {response.status_code}")
            response.raise_for_status()
            
            data = response.json()
            # print(f"[DEBUG] Response keys: {list(data.keys())}")
            
            related_words = []
            
            # Extract wikitext content
            query = data.get('query', {})
            # print(f"[DEBUG] Query keys: {list(query.keys())}")
            
            pages = query.get('pages', [])
            # print(f"[DEBUG] Number of pages returned: {len(pages)}")
            
            if not pages:
                print("[DEBUG] No pages returned from API")
                return []
            
            page = pages[0]
            # print(f"[DEBUG] Page keys: {list(page.keys())}")
            # print(f"[DEBUG] Page ID: {page.get('pageid', 'N/A')}")
            # print(f"[DEBUG] Page title: {page.get('title', 'N/A')}")
            
            if 'missing' in page:
                print(f"[DEBUG] Page is missing: {page.get('missing')}")
                return []
            
            if 'revisions' not in page:
                # print("[DEBUG] No revisions in page")
                return []
            
            revisions = page.get('revisions', [])
            # print(f"[DEBUG] Number of revisions: {len(revisions)}")
            
            if not revisions:
                print("[DEBUG] Revisions list is empty")
                return []
            
            wikitext = revisions[0].get('content', '')
            # print(f"[DEBUG] Wikitext length: {len(wikitext)} characters")
            # print(f"[DEBUG] Wikitext preview (first 500 chars): {wikitext[:300]}")
            
            # Hebrew Unicode range: 0590-05FF
            hebrew_pattern = re.compile(r'[\u0590-\u05FF]+')
            
            # Extract Hebrew words from wikitext
            # Look for links [[word]] which are common in wikitext
            link_pattern = re.compile(r'\[\[([^\]]+)\]\]')
            links = link_pattern.findall(wikitext)
            print(f"[DEBUG] Found {len(links)} links in wikitext")
            print(f"[DEBUG] First 10 links: {links[:10]}")
            
            for link in links:
                # Remove pipe ([[word|display]]) and parentheses
                base = link.split('|')[0]
                self.extract_words_from_wikitext_phrase(word, base, related_words, max_words)

            print(f"[DEBUG] After processing links, found {len(related_words)} related words")
            
            # Also extract any Hebrew words from the wikitext content
            if len(related_words) < max_words:
                print(f"[DEBUG] Need more words, extracting all Hebrew words from wikitext...")
                all_hebrew_words = hebrew_pattern.findall(wikitext)
                print(f"[DEBUG] Found {len(all_hebrew_words)} total Hebrew words in wikitext")
                print(f"[DEBUG] First 20 Hebrew words: {all_hebrew_words[:20]}")
                
                for found_word in all_hebrew_words:
                    self.extract_words_from_wikitext_phrase(word, found_word, related_words, max_words)
           
            print(f"[DEBUG] Final result: {len(related_words)} related words: {related_words}")
            #time.sleep(1000)
            return related_words[:max_words]
            
        except requests.exceptions.RequestException as e:
            print(f"[DEBUG] RequestException: {e}")
            print(f"[DEBUG] Response text (if available): {getattr(e.response, 'text', 'N/A')[:500]}")
            return []
        except (KeyError, IndexError) as e:
            print(f"[DEBUG] KeyError/IndexError: {e}")
            print(f"[DEBUG] Data structure: {json.dumps(data, ensure_ascii=False, indent=2)[:1000]}")
            return []
        except Exception as e:
            print(f"[DEBUG] Unexpected error: {type(e).__name__}: {e}")
            import traceback
            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            return []


    def get_word_to_try(self) -> str:
        top_matches = self.get_top_matches(5)
        for top_match in top_matches:
            word = top_match['word']
            related_words = self.get_cached_related_words(word, 150)
            available_words = [w for w in related_words if w not in self.tried_words]
            if len(available_words) > 0:
                return random.choice(available_words)
            
        return self.get_random_word()


    
    def auto_solve(self) -> str:
        print(f"Starting autonomous solving with seed word: {self.format_hebrew(self.seed_word)}")
        print("="*60)
       
        # Continue autonomously until we find the answer or run out of words
        while True:

            word_to_try = self.get_word_to_try()
            result = self.submit_guess(word_to_try)
            self.tried_words.add(word_to_try)

            if result:
                similarity = result['similarity']
                self.display_result(result)
                if similarity == 100 or len(self.tried_words) % 15 == 0:
                    print(f"\n{'='*60}")
                    print(f"Progress Update (Total words tried: {len(self.tried_words)})")
                    print("="*60)
                    self.show_top_matches(10)

                if similarity == 100:
                    print("🎉 FOUND THE ANSWER! 🎉")
                    return result['word']
                    
            # Small delay to avoid overwhelming the API
            time.sleep(0.1)


def main():
    """Main function for interactive use or autonomous mode"""
    solver = SemantleSolver()
    
    if len(sys.argv) > 1:
        seed_word = ' '.join(sys.argv[1:])
        normalized_seed = solver.normalize_hebrew_input(seed_word)
    else:
        normalized_seed = solver.get_random_word()

    print(f"Starting fully autonomous mode with seed word: {solver.format_hebrew(normalized_seed)}")
    solver.seed_word = normalized_seed
    solver.auto_solve()
    return


if __name__ == "__main__":
    main()
