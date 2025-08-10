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
            pfp_url = user.profile_image_url.replace('_normal', '')
            print(f"Found PFP URL: {pfp_url}")
            return pfp_url, None
        except Exception as e:
            print(f"❌ An error occurred. The user '{username}' may not exist or their profile is protected. Error: {e}")
            return None, f"User '{username}' not found or profile is protected."

    def do_GET(self):
        # Parse the URL and query parameters
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        username = query_params.get('username', [None])[0]

        if not username:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Username parameter is missing'}).encode('utf-8'))
            return

        # Run the asynchronous function to get the PFP URL
        pfp_url, error = asyncio.run(self.get_pfp_url(username))

        if error:
            self.send_response(404) # Not Found or other error
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': error}).encode('utf-8'))
            return
        
        # If successful, send the URL back
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        # Add CORS header to allow requests from your front-end, especially during local development
        self.send_header('Access-Control-Allow-Origin', '*') 
        self.end_headers()
        
        response_data = {'pfp_url': pfp_url}
        self.wfile.write(json.dumps(response_data).encode('utf-8'))
        return