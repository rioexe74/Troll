import asyncio
import httpx
import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from twikit.guest import GuestClient

# This is the main entry point for the Vercel serverless function
class handler(BaseHTTPRequestHandler):

    async def get_pfp_url(self, username: str):
        """
        Fetches a user's high-resolution profile picture URL using their username.
        This is a modified version of your original script.
        """
        print(f"Attempting to fetch PFP URL for: {username}")
        
        try:
            client = GuestClient()
            print("Activating guest client...")
            await client.activate()
        except Exception as e:
            print(f"Error: Could not activate the guest client. {e}")
            return None, f"Could not activate the guest client: {e}"

        try:
            print(f"Fetching data for '{username}'...")
            user = await client.get_user_by_screen_name(username)

            # Get the high-resolution profile picture URL by removing '_normal'
            pfp_url = (user.profile_image_url or '').replace('_normal', '')
            display_name = getattr(user, 'name', '') or ''
            screen_name = getattr(user, 'screen_name', '') or username
            print(f"Found PFP URL: {pfp_url} | name: {display_name} | handle: @{screen_name}")
            return {"pfp_url": pfp_url, "name": display_name, "handle": f"@{screen_name}"}, None
        except Exception as e:
            print(f"❌ An error occurred. The user '{username}' may not exist or their profile is protected. Error: {e}")
            return None, f"User '{username}' not found or profile is protected."

    def do_GET(self):
        # Parse the URL and query parameters
        parsed_url = urlparse(self.path)
        path = parsed_url.path or '/'
        query_params = parse_qs(parsed_url.query)

        # Simple router: /pfp for profile data, /image for proxying image bytes, / defaults to /pfp
        if path == '/image':
            image_url = query_params.get('url', [None])[0]
            if not image_url:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'url parameter is missing'}).encode('utf-8'))
                return

            try:
                # Proxy the remote image to avoid canvas taint and CORS issues
                default_headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                    'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Referer': 'https://imgur.com/'
                }
                with httpx.Client(follow_redirects=True, timeout=20.0, headers=default_headers) as client:
                    resp = client.get(image_url)
                    resp.raise_for_status()
                    content_type = resp.headers.get('content-type', 'image/jpeg')

                    self.send_response(200)
                    self.send_header('Content-type', content_type)
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Cache-Control', 'public, max-age=3600')
                    self.end_headers()
                    self.wfile.write(resp.content)
                    return
            except Exception as e:
                self.send_response(502)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': f'Failed to fetch image: {e}'}).encode('utf-8'))
                return

        # Default and /pfp: return profile data
        if path in ('/', '/pfp'):
            username = query_params.get('username', [None])[0]

            if not username:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Username parameter is missing'}).encode('utf-8'))
                return

            # Run the asynchronous function to get the profile data
            result, error = asyncio.run(self.get_pfp_url(username))

            if error:
                self.send_response(404)  # Not Found or other error
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': error}).encode('utf-8'))
                return

            # If successful, send the data back
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
            return

        # Unknown route
        self.send_response(404)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({'error': 'Not found'}).encode('utf-8'))
        return