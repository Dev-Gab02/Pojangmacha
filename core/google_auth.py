import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Scopes needed to access user info
SCOPES = ['https://www.googleapis.com/auth/userinfo.email',
          'https://www.googleapis.com/auth/userinfo.profile',
          'openid']

def get_google_user_info(force_new_login=False):
    """
    Authenticate with Google and return user info
    Args:
        force_new_login: If True, always show account selection
    Returns: dict with 'email', 'name', 'picture' or None if failed
    """
    creds = None
    token_file = 'token.json'
    
    # If force_new_login, delete existing token to show account picker
    if force_new_login and os.path.exists(token_file):
        os.remove(token_file)
        print("🔄 Forcing new Google login...")
    
    # Check if token already exists
    if os.path.exists(token_file):
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)
    
    # If no valid credentials, let user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Refresh expired token
            creds.refresh(Request())
        else:
            # Start OAuth flow with account selection prompt
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                
                # Force account selection every time
                flow.authorization_url(prompt='select_account')
                
                creds = flow.run_local_server(
                    port=0,
                    prompt='select_account',  # Force Google account picker
                    authorization_prompt_message='Please select your Google account in the browser...'
                )
            except Exception as e:
                print(f"OAuth error: {e}")
                return None
        
        # Save credentials for next time
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)
    
    try:
        # Build People API service
        service = build('people', 'v1', credentials=creds)
        
        # Get user info
        results = service.people().get(
            resourceName='people/me',
            personFields='emailAddresses,names,photos'
        ).execute()
        
        # Extract user data
        email = results['emailAddresses'][0]['value'] if 'emailAddresses' in results else None
        name = results['names'][0]['displayName'] if 'names' in results else None
        picture = results['photos'][0]['url'] if 'photos' in results else None
        
        return {
            'email': email,
            'name': name,
            'picture': picture
        }
    
    except Exception as e:
        print(f"Error getting user info: {e}")
        return None

def revoke_google_auth():
    """Logout - delete saved token"""
    token_file = 'token.json'
    if os.path.exists(token_file):
        os.remove(token_file)
        print("Google authentication revoked")