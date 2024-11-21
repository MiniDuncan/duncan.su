from flask import Flask, request, jsonify, render_template, redirect
import requests
import re

app = Flask(__name__)

# Global User-Agent and base URL
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
base_url = 'https://streamed.su/api'

# Helper function to fetch matches by sport
def get_matches(sport=None, popular=False, live=False, today=False):
    headers = {'User-Agent': UA}
    url = f"{base_url}/matches/"
    
    if sport:
        url += sport
    else:
        url += "all"

    if popular:
        url += "/popular"
    elif live:
        url += "/live"
    elif today:
        url += "/all-today"

    try:
        response = requests.get(url, headers=headers, timeout=10)
        matches = response.json()
    except Exception as e:
        print(f"Error fetching matches: {e}")
        return []

    return matches

# Helper function to fetch sports categories
def get_sports():
    headers = {'User-Agent': UA}
    url = f"{base_url}/sports"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        sports = response.json()
    except Exception as e:
        print(f"Error fetching sports: {e}")
        return []

    return sports

# Route to play stream
@app.route('/play/<event_name>')
def play_stream(event_name):
    print(f"Received request to play: {event_name}")
    
    # Use the original m3u8 playlist URL
    m3u_playlist_url = 'https://bit.ly/duncansu'
    
    try:
        print("Fetching m3u content...")  # Indicate that we're fetching the m3u
        response = requests.get(m3u_playlist_url)
        m3u_content = response.text
        
        # Log the m3u content for debugging purposes
        print("Fetched m3u content:", m3u_content[:500])  # Limiting the log to the first 500 characters
        
        # Find the specific stream URL for the event
        stream_url = find_stream_url(m3u_content, event_name)
        
        if stream_url:
            print(f"Stream URL for {event_name}: {stream_url}")
            # Return the stream URL without any proxying
            return render_template('player_embed.html', m3u_url=stream_url)
        else:
            print(f"No stream found for {event_name}")
            return f"No stream found for {event_name}", 404

    except Exception as e:
        print(f"Error fetching the m3u playlist: {e}")
        return "Error fetching playlist", 500

# Helper function to find the stream URL from the m3u content
import difflib

def find_stream_url(m3u_content, event_name):
    """
    Search the m3u content for the given event name (tvg-name) and return the corresponding stream URL.
    If no exact match is found, look for keywords in the event name with improved matching.
    """
    pattern = re.compile(r'#EXTINF:-1 .*tvg-name="([^"]+).*",(.+)\n(.+)')
    
    # Store all matches in a list to iterate multiple times
    matches = list(pattern.finditer(m3u_content))

    # Try to match the exact event name first
    for match in matches:
        tvg_name = match.group(2).strip()
        stream_url = match.group(3).strip()
        
        # Check if the event name matches exactly (case-insensitive)
        if difflib.SequenceMatcher(None, event_name.lower(), tvg_name.lower()).ratio() > 0.8:
            return stream_url

    # If no exact match, try to find keyword matches with improved logic
    best_match_score = 0
    best_match_url = None

    # Split event name into relevant terms, ignoring common words like "vs", "v", and "at"
    ignore_keywords = ["vs", "v", "at", "women", "men", "live"]
    event_keywords = [word for word in event_name.split() if word.lower() not in ignore_keywords]

    for match in matches:
        tvg_name = match.group(2).strip()
        stream_url = match.group(3).strip()
        
        # Score the tvg_name based on how many relevant keywords from event_name it contains
        match_score = sum(1 for keyword in event_keywords if keyword.lower() in tvg_name.lower())

        # Use fuzzy matching for remaining score improvements
        fuzzy_score = difflib.SequenceMatcher(None, event_name.lower(), tvg_name.lower()).ratio()
        match_score += fuzzy_score * 0.5  # Adjust the weight of fuzzy matching as needed

        # If the match score is better than the previous best, update
        if match_score > best_match_score:
            best_match_score = match_score
            best_match_url = stream_url

    # Return the best match if found, otherwise None
    return best_match_url if best_match_score > 0 else None
    
# Main menu route
@app.route('/')
def main_menu():
    menu = [
        {'title': 'ALL SPORTS STREAMS', 'url': '/schedule'},
    ]
    return render_template('menu.html', menu=menu)

# Schedule route to show categories
@app.route('/schedule')
def schedule():
    sports = get_sports()
    return render_template('schedule.html', sports=sports)

# Matches for a specific sport
@app.route('/matches/<sport>')
def matches(sport):
    matches = get_matches(sport=sport)
    
    # Only filter out matches with no posters if the sport is "football"
    if sport.lower() == 'football':
        matches = [
            match for match in matches
            if match.get('poster') and match['poster'] != '/'
        ]

    return render_template('channels.html', categ=sport, events=matches)



# Today's matches
@app.route('/matches/today')
def matches_today():
    matches = get_matches(today=True)
    return render_template('channels.html', categ="Today's Matches", events=matches)

# Live matches
@app.route('/matches/live')
def live_matches():
    matches = get_matches(live=True)
    return render_template('channels.html', categ="Live Matches", events=matches)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
