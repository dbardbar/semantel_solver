import argparse
import requests
import json
import re
import time
import sys
import random
import unicodedata
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from urllib.parse import quote, urlencode
from typing import TypedDict
from bs4 import BeautifulSoup



# Unicode Right-to-Left Mark for proper Hebrew display
RTL_MARK = '\u200F'

class WordToTry(TypedDict):
    word: str
    origin: str
    origin_source: str

class GuessResult(TypedDict):
    word: str
    similarity: float
    distance: int
    origin: str
    origin_source: str
    guess_number: int

class SemantleSolver:
    def __init__(self):
        self.api_url_hebrew = "https://semantle.ishefi.com/api/distance"
        self.api_url_english = "https://server.semantle.com/similarity/__WORD__/__SECRET__/en"
        #                       https://server.semantle.com/similarity/half/reserve/en
        self.guess_history: list[GuessResult] = []
        self.tried_words: set[str] = set()  # Track words already tried
        self.corpus: list[str] = []  # Hebrew word corpus for random guesses
        self.corpus_loaded = False
        self.wikipedia_cache: dict[str, list[str]] = {}
        self.wikipedia_exhausted: list[str] = []
        self.milog_cache: dict[str, list[str]] = {}
        self.milog_exhausted: list[str] = []
        self.seed_word = ""
        self.language = "hebrew"
        self.puzzle_number = 1460
        self.secret_word = ""
        self.top_words_to_find_relations = 70
    
    def load_corpus(self) -> None:
        if self.corpus_loaded:
            return
        
        print("Loading word corpus...")
        
        if self.language == "hebrew":
            word_files = [ "wordlist_he.txt" ]
        else:
            word_files = [ "wordlist_en.txt" ]
                
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

        common_english_words = [
            "democracy", "photosynthesis", "gravity", "evolution", "renaissance",
            "capitalism", "socialism", "algorithm", "encryption", "internet",
            "neuron", "genome", "quantum", "relativity", "thermodynamics",
            "volcano", "earthquake", "tsunami", "climate", "biodiversity",
            "ecosystem", "antibiotic", "vaccination", "pandemic", "immunology",
            "psychology", "cognition", "linguistics", "semantics", "syntax",
            "philosophy", "ethics", "metaphysics", "logic", "aesthetics",
            "mythology", "religion", "buddhism", "christianity", "islam",
            "judaism", "astronomy", "galaxy", "planet", "asteroid",
            "cosmology", "blackhole", "robotics", "automation",
            "artificialintelligence", "machinelearning", "statistics",
            "probability", "economics", "inflation", "recession", "currency",
            "trade", "architecture", "engineering", "aerodynamics",
            "nanotechnology", "biotechnology", "genetics", "archaeology",
            "anthropology", "sociology", "urbanization", "globalization",
            "imperialism", "colonialism", "nationalism", "revolution",
            "constitution", "literature", "poetry", "novel", "theatre",
            "cinema", "photography", "music", "orchestra", "jazz",
            "classicalmusic", "olympics", "football", "basketball",
            "nutrition", "metabolism", "diabetes", "cancer", "neuroscience",
             "consciousness", "biome", "fossil", "paleontology", "seismology", "glacier",
            "hurricane", "tornado", "deforestation", "pollution", "renewableenergy",
            "photosphere", "supernova", "exoplanet", "nebula", "darkmatter",
            "stringtheory", "nanomaterials", "semiconductor", "blockchain",
            "cryptocurrency", "cybersecurity", "dataanalysis", "bigdata",
            "cloudcomputing", "internetofthings", "virtualreality", "augmentedreality",
            "geneticengineering", "stemcells", "immunotherapy", "epidemiology",
            "neuroplasticity", "behaviorism", "culturalstudies", "feminism",
            "existentialism", "stoicism", "utilitarianism", "nihilism",
            "monotheism", "polytheism", "hinduism", "shinto", "taoism",
            "planetaryscience", "astrophysics", "cosmogony", "mechatronics",
            "automationengineering", "algorithmics", "cryptography", "heuristics",
            "supplychain", "macroeconomics", "microeconomics", "mercantilism",
            "feudalism", "colonization", "decolonization", "suffrage",
            "humanrights", "civilization", "mythopoeia", "epicpoetry",
            "drama", "painting", "sculpture", "impressionism", "cubism",
            "symphony", "opera", "ballet", "rugby", "cricket", "tennis",
            "obesity", "hypertension", "cardiology", "oncology", "virology",
            "cognitivebias", "memory", "learning", "neurotransmitter"
        ]


        if self.language == "hebrew":
            common_words = common_hebrew_words
        if self.language == "english":
            common_words = common_english_words
        
        words_set = set()

        for word_file in word_files:
            try:
                with open(word_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        word = line.strip()
                        words_set.add(word)
            except Exception as e:
                print(f"Exception while loading {word_file}")
                continue
            print(f"Loaded {len(words_set)} words from {word_file}")
            break

        # Add common words as fallback
        for word in common_words:
            words_set.add(word)
        
        self.corpus = list(words_set)
        self.corpus_loaded = True
        print(f"Corpus loaded: {len(self.corpus)} words available")
    
    def get_random_words_from_corpus(self, count: int =5) -> list[str]:
        """Get random words from corpus, excluding already tried words"""
        if not self.corpus_loaded:
            self.load_corpus()
        
        # Filter out already tried words
        available_words = [w for w in self.corpus if w not in self.tried_words]
        
        if not available_words:
            return []
        
        # Return random sample
        sample_size = min(count, len(available_words))
        return random.sample(available_words, sample_size)
    
    def get_random_unused_word(self) -> str | None:
        words = self.get_random_words_from_corpus(1)
        if len(words) > 0:
            return words[0]
        return None

    
    def submit_guess(self, word_to_try: WordToTry, sleep_time: float = 5) -> GuessResult | None:
        word = word_to_try["word"]
        origin = word_to_try["origin"]
        origin_source = word_to_try["origin_source"]

        if word in self.tried_words:
            return None
        
        # URL encode the Hebrew word
        encoded_word = quote(word)
        if self.language == "hebrew":
            url = f"{self.api_url_hebrew}?word={encoded_word}"
        if self.language == "english":
            url = self.api_url_english.replace("__WORD__", encoded_word).replace("__SECRET__", self.secret_word)
        
        try:
            response = requests.get(url)

            if response.status_code == 429:
                print(f"Rate limit exceeded for word: {self.format_hebrew(word)}")
                time.sleep(sleep_time)
                return self.submit_guess(word_to_try, sleep_time*1.5)

            self.tried_words.add(word)
            guess_number = len(self.tried_words)

            if response.status_code == 400 or response.status_code == 404:
                error_text = response.text
                if "Word not found" in error_text:
                    # print(f"Word not found in game dictionary: {self.format_hebrew(word)}")

                    result: GuessResult = {
                        "word": word,
                        "similarity": -1,
                        "distance": -1,
                        "origin": origin,
                        "origin_source": origin_source,
                        "guess_number": guess_number
                    }
                    self.guess_history.append(result)
                    return result
                else:
                    # Other 400 error
                    print(f"API error (400): {error_text}")
                    return None
            
            response.raise_for_status()
            data = response.json()

            if self.language == "hebrew":
                similarity = float(data[0].get("similarity", 0.0))
                distance = int(data[0].get("distance", 0))
            if self.language == "english":
                similarity = float(data.get("similarity", 0.0))
                if data.get("percentile") == None:
                    distance = 0
                else:
                    distance = int(data.get("percentile", 0))


            result: GuessResult = {
                "word": word,
                "similarity": similarity,
                "distance": distance,
                "origin": origin,
                "origin_source": origin_source,
                "guess_number": guess_number
            }
            self.guess_history.append(result)
            return result
                
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error making API request: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Error making API request: {e}")
            return None
    
    def is_hebrew(self, text: str) -> bool:
        if not text:
            return False
        return all('\u0590' <= char <= '\u05FF' for char in str(text))
       
    def format_hebrew(self, text: str) -> str:
        """Format Hebrew text for proper display in terminal"""
        if not text or text == 'N/A':
            return str(text)
        
        text_str = str(text)
        if self.is_hebrew(text_str):
            return text_str[::-1]
        return text_str
    

    def get_top_matches(self, n: int = 10) -> list[GuessResult]:
        """Get top N matches by similarity"""
        sorted_history = sorted(self.guess_history, 
                               key=lambda x: x['similarity'], 
                               reverse=True)
        return sorted_history[:n]
    

    def display_result(self, result: GuessResult) -> None:
        if result is None:
            print("No result to display")
            return
        word = self.format_hebrew(result['word'])
        similarity = result['similarity']
        distance = result['distance']
        origin = self.format_hebrew(result['origin'])
        print(f"#{result['guess_number']:<4} {word:20} Sim: {similarity:6.2f} Dist: {distance:4} Origin: {origin} ({result['origin_source']})" )
    
    def show_top_matches(self, n: int = 15) -> None:
        top_matches = self.get_top_matches(n)
        if not top_matches:
            print("No guesses made yet.")
            return
        
        print("\n" + "="*75)
        print(f"TOP {len(top_matches)} BEST MATCHES")
        print("="*75)
        for guess in top_matches:
            self.display_result(guess)
        print("="*75 + "\n")

        
    def print_word_path(self, result: GuessResult) -> None: 
        self.display_result(result)
        origin = result["origin"]
        if len(origin) == 0:
            return
        for r in self.guess_history:
            if r["word"] == origin:
                self.print_word_path(r)          
        return
    

    def remove_niqqud(self, text: str) -> str:
        return ''.join(
            ch for ch in text
            if unicodedata.category(ch) != 'Mn'
        )

    SPECIAL_CHARS = "־()#|:[]{}<>.,;!?+-=_\"'"

    TRANS_TABLE = str.maketrans({c: " " for c in SPECIAL_CHARS})


    def extract_words_from_wikitext_phrase(self, base_word: str, phrase, related_words, max_words: int) -> None:
        # phrase = phrase.replace('(', ' ').replace(')', ' ').replace('|', ' ').replace(':', ' ').strip()
        phrase = phrase.translate(self.TRANS_TABLE).strip()

        for word in phrase.split():
            word = self.remove_niqqud(word)
            if self.language == "english":
                word = word.lower()
            if self.language == "hebrew" and not self.is_hebrew(word):
                continue

            if (len(word) < 2 or word == base_word or word in self.tried_words or word in related_words):
                continue

            related_words.append(word)
            if len(related_words) >= max_words:
                break


    def get_cached_milog_related_words(self, word: str, max_words: int = 30) -> list[str]:
        """Get related words from cache if available"""

        if word in self.milog_exhausted:
            return []

        if word in self.milog_cache:
             return self.milog_cache[word]

        related_words = self.get_related_words_from_milog(word, max_words)
        self.milog_cache[word] = related_words
        if len(related_words) == 0:
            self.milog_exhausted.append(word)

        return related_words



    def get_cached_wikipedia_related_words(self, word: str, max_words: int = 30) -> list[str]:
        if word in self.wikipedia_exhausted:
            return []

        if word in self.wikipedia_cache:
             return self.wikipedia_cache[word]

        related_words = self.get_related_words_from_wikipedia(word, max_words)
        self.wikipedia_cache[word] = related_words
        if len(related_words) == 0:
            self.wikipedia_exhausted.append(word)

        return related_words


    def normalize_hebrew_token(self, text: str) -> str:
        text = self.remove_niqqud(text)
        text = text.replace('־', ' ')  # maqaf
        return text.strip()

    HEBREW_WORD_RE = re.compile(r'[\u05D0-\u05EA]{2,}')

    def get_related_words_from_milog(self, word: str, max_words: int) -> list[str]:
        api_url = "https://milog.co.il/"
        headers = {
            'User-Agent': 'SemantleSolver/1.0 (https://github.com/yourusername/semantle-solver)'
        }
        url = api_url + quote(word)
        try:
            response = requests.get(url , headers=headers, timeout=10)
            print(f"[DEBUG] Milog response status code: {response.status_code}")
            response.raise_for_status()
            html = response.content
            soup = BeautifulSoup(html, "lxml")
            #print(f"[DEBUG] milog raw content: {html}")
            raw_words = []
            related_words = []
            for div in soup.find_all("div", class_="sr_e"):
                text = div.get_text(separator=" ", strip=True)
                text = self.normalize_hebrew_token(text)
                for candidate in self.HEBREW_WORD_RE.findall(text):
                    if (candidate == word or candidate in self.tried_words or candidate in related_words):
                        continue
                    related_words.append(candidate)
                    if len(related_words) >= max_words:
                        break

            final = related_words[:max_words]
            print(f"[DEBUG] Milog final result: {len(related_words)} related words, returning {max_words}: {final}")
            return final
        except Exception as e:
            print(f"[DEBUG] Unexpected error: {type(e).__name__}: {e}")
            import traceback
            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            return []


    def get_related_words_from_wikipedia(self, word: str, max_words: int) -> list[str]:
        """
        Fetch related words from Wiktionary Hebrew page using MediaWiki API
        
        Args:
            word: Hebrew word to look up
            max_words: Maximum number of related words to return
            
        Returns:
            list: List of related Hebrew words
        """
        
        print(f"\n[DEBUG] Wiktionary lookup for word: {self.format_hebrew(word)} max_word {max_words}")
        
        # Use MediaWiki Action API for Hebrew Wiktionary
        if self.language == "hebrew":
            api_url = "https://he.wikipedia.org/w/api.php"
        if self.language == "english":
            api_url = "https://en.wikipedia.org/w/api.php"
        
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
            
            
            # Extract Hebrew words from wikitext
            # Look for links [[word]] which are common in wikitext
            link_pattern = re.compile(r'\[\[([^\]]+)\]\]')
            links = link_pattern.findall(wikitext)
            print(f"[DEBUG] Found {len(links)} links in wikitext")
            print(f"[DEBUG] First 10 links: {links[:10]}")
            
            for link in links:
                # Remove pipe ([[word|display]]) and parentheses
                #base = link.split('|')[0]
                self.extract_words_from_wikitext_phrase(word, link, related_words, max_words)

            print(f"[DEBUG] After processing links, found {len(related_words)} related words - {related_words}")

            # Also extract any Hebrew words from the wikitext content
            # TODO - think how to extract from English wiki
            if self.language == "hebrew" and len(related_words) < max_words:
                print(f"[DEBUG] Need more words, extracting all words from wikitext...")
                # Hebrew Unicode range: 0590-05FF
                hebrew_pattern = re.compile(r'[\u0590-\u05FF]+')
                all_hebrew_words = hebrew_pattern.findall(wikitext)
                print(f"[DEBUG] Found {len(all_hebrew_words)} total words in wikitext")
                print(f"[DEBUG] First 20 Hebrew words: {all_hebrew_words[:20]}")
                
                for found_word in all_hebrew_words:
                    self.extract_words_from_wikitext_phrase(word, found_word, related_words, max_words)

            final = related_words[:max_words]
            print(f"[DEBUG] Final result: {len(related_words)} related words, returning {max_words}: {final}")
            #time.sleep(1000)
            return final
            
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


    def get_word_to_try_from_related_word(self, top_matches_to_search: int) -> WordToTry | None:
        top_matches = self.get_top_matches(70)
        for top_match in top_matches:
            word = top_match['word']
            related_words = self.get_cached_wikipedia_related_words(word, 30)
            available_words = [w for w in related_words if w not in self.tried_words]
            if len(available_words) > 0:
                chosen_word = random.choice(available_words)
                return WordToTry(word=chosen_word, origin=word, origin_source="wiki")

            if not self.language == "hebrew":
                continue
            related_words = self.get_cached_milog_related_words(word, 30)
            available_words = [w for w in related_words if w not in self.tried_words]
            if len(available_words) > 0:
                chosen_word = random.choice(available_words)
                return WordToTry(word=chosen_word, origin=word, origin_source="milog")

        return None

    def get_word_to_try(self) -> WordToTry | None:
        word_to_try = self.get_word_to_try_from_related_word(self.top_words_to_find_relations)
        if word_to_try:
            return word_to_try

        if self.seed_word and self.seed_word not in self.tried_words:
            return WordToTry(word=self.seed_word, origin="", origin_source="seed")

        # This is to avoid going too much into the random words if there are no wiki articles for top words
        self.top_words_to_find_relations += 1
        print(f"Increasing the top words to fins relations from to {self.top_words_to_find_relations}")
            
        random_word = self.get_random_unused_word()
        if random_word:
            return WordToTry(word=random_word, origin="", origin_source="random")

        # Last ditch attempt - get ANY related word. Anything goes.
        return self.get_word_to_try_from_related_word(1000000000)
    
    def get_english_secret_word(self) -> str:
        url = f"https://server.semantle.com/semantle/game/{self.puzzle_number}/en"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        #print(data)
        secret_word = data['secretWord']
        if secret_word is None or len(secret_word) < 1:
            raise Exception
        #print(f"Secret word is {secret_word}")
        return secret_word

    def calculate_english_puzzle_number(self) -> int:
        START_DATE = date(2022, 1, 29)
        ROLLOVER_HOUR = 20  # 8 PM Eastern
        tz = ZoneInfo("America/New_York")
        now_ny = datetime.now(tz)
        if now_ny.hour < ROLLOVER_HOUR:
            game_date = now_ny.date() - timedelta(days=1)
        else:
            game_date = now_ny.date()

        return (game_date - START_DATE).days + 1


    def auto_solve(self) -> str:
        print(f"Starting autonomous solving with seed word: {self.format_hebrew(self.seed_word)}")
        if self.language == "english":
            if self.puzzle_number == None:
                self.puzzle_number = self.calculate_english_puzzle_number()
            print(f"Solving English puzzle number {self.puzzle_number}")
            self.secret_word = self.get_english_secret_word()
        print("="*70)
            
        # Continue autonomously until we find the answer or run out of words
        while True:
            word_to_try = self.get_word_to_try()
            if word_to_try == None:
                print("Failed to find word. Exhausted all word sources")
                return

            result = self.submit_guess(word_to_try)
            #self.tried_words.add(word_to_try["word"])

            if result:
                distance = result['distance']
                self.display_result(result)
                if distance == 1000 or len(self.tried_words) % 15 == 0:
                    print(f"\n{'='*60}")
                    print(f"Progress Update (Total words tried: {len(self.tried_words)})")
                    print("="*60)
                    self.show_top_matches(15)

                if distance == 1000:
                    print("🎉 FOUND THE ANSWER! 🎉")
                    print("Path:")
                    self.print_word_path(result)
                    return result['word']


            if len(self.tried_words) % 200 == 0:
                self.flush_dictionary(self.wikipedia_cache, "wiki")
                self.flush_dictionary(self.milog_cache, "milog")

            # Small delay to avoid overwhelming the API
            time.sleep(0.1)


    def flush_dictionary(self, dictionary_to_flush: dict[str, list[str]], description: str) -> None:
        words_before = len(dictionary_to_flush)
        total_before = sum(len(v) for v in dictionary_to_flush.values())
        dictionary_to_flush.clear()
        print(f"Doing a flush of the {description} cache - size before {words_before}/{total_before}")




class SolverOptions(TypedDict):
    language: str
    seed_word: str | None
    puzzle_number: int | None


def normalize_hebrew_input(text: str) -> str:
    # keep simple for now; assumes Hebrew only
    return text[::-1]


def parse_args() -> SolverOptions:
    parser = argparse.ArgumentParser(
        description="Autonomous Semantle solver (Hebrew / English)"
    )

    parser.add_argument(
        "-l", "--language",
        choices=["hebrew", "english"],
        default="hebrew",
        help="Game language (default: hebrew)"
    )

    parser.add_argument(
        "-s", "--seed",
        metavar="WORD",
        help="Seed word to try first"
    )

    parser.add_argument(
        "-n", "--number",
        dest="puzzle_number",
        type=int,
        default=None,
        help="English puzzle number to solve (default: auto find today)"
    )

    args = parser.parse_args()

    seed_word = args.seed
    if seed_word and args.language == "hebrew":
        seed_word = normalize_hebrew_input(seed_word)

    return SolverOptions(
        language=args.language,
        seed_word=seed_word,
        puzzle_number=args.puzzle_number
    ) 

def main() -> None:
    options = parse_args()
    solver = SemantleSolver()
    solver.language = options['language']
    solver.seed_word = options['seed_word']
    solver.puzzle_number = options['puzzle_number']
    solver.auto_solve()


if __name__ == "__main__":
    main()
