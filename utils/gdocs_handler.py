import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]

def get_google_credentials():
    """
    Handles OAuth2 flow and returns authorized credentials.
    """
    creds = None
    token_path = os.path.join('credentials', 'token.json')
    creds_path = os.path.join('credentials', 'google_creds.json')

    # Fallback to root level if files exist there instead of the credentials folder
    if not os.path.exists(creds_path) and os.path.exists('google_creds.json'):
        creds_path = 'google_creds.json'
    if not os.path.exists(token_path) and os.path.exists('token.json'):
        token_path = 'token.json'

    # Load cached tokens if they exist
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    # If credentials are not valid or don't exist, authenticate the user
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        
        if not creds:
            if not os.path.exists(creds_path):
                raise FileNotFoundError(
                    f"Google OAuth credentials not found at '{creds_path}'. "
                    "Please create this file with your OAuth 2.0 Client IDs to authenticate."
                )
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save token for subsequent runs
        os.makedirs('credentials', exist_ok=True)
        with open(token_path, 'w') as token_file:
            token_file.write(creds.to_json())
            
    return creds

def get_gdocs_service():
    """
    Returns the Google Docs and Drive API clients using shared credentials.
    """
    creds = get_google_credentials()
    docs_service = build('docs', 'v1', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    return docs_service, drive_service

def make_shareable(doc_id: str, docs_service, drive_service) -> None:
    """
    Updates the permissions of a file in Google Drive to make it viewable by anyone.
    """
    permission = {
        'type': 'anyone',
        'role': 'reader'
    }
    drive_service.permissions().create(
        fileId=doc_id,
        body=permission,
        fields='id'
    ).execute()

def parse_markdown_to_gdocs(content: str):
    """
    Parses raw markdown text, strips H1/H2/H3 symbols, and calculates
    character ranges to apply Google Docs heading styles.
    """
    lines = content.split('\n')
    cleaned_lines = []
    heading_ranges = []
    current_char_count = 1  # Google Docs document indices are 1-based
    
    for line in lines:
        stripped = line.strip()
        
        # Check H1
        if stripped.startswith('#') and not stripped.startswith('##'):
            text = stripped.lstrip('#').strip().replace('**', '').replace('*', '')
            cleaned_lines.append(text)
            start = current_char_count
            end = start + len(text)
            heading_ranges.append({'startIndex': start, 'endIndex': end, 'style': 'HEADING_1'})
            current_char_count += len(text) + 1  # +1 for newline
            
        # Check H2
        elif stripped.startswith('##') and not stripped.startswith('###'):
            text = stripped.lstrip('#').strip().replace('**', '').replace('*', '')
            cleaned_lines.append(text)
            start = current_char_count
            end = start + len(text)
            heading_ranges.append({'startIndex': start, 'endIndex': end, 'style': 'HEADING_2'})
            current_char_count += len(text) + 1
            
        # Check H3
        elif stripped.startswith('###'):
            text = stripped.lstrip('#').strip().replace('**', '').replace('*', '')
            cleaned_lines.append(text)
            start = current_char_count
            end = start + len(text)
            heading_ranges.append({'startIndex': start, 'endIndex': end, 'style': 'HEADING_3'})
            current_char_count += len(text) + 1
            
        else:
            # Regular paragraph
            cleaned_lines.append(line)
            current_char_count += len(line) + 1
            
    full_text = '\n'.join(cleaned_lines)
    return full_text, heading_ranges

def create_doc(title: str, content: str) -> str:
    """
    Creates a new Google Doc, parses and applies heading styles,
    makes it public-readable, and returns the shareable URL.
    """
    docs_service, drive_service = get_gdocs_service()
    
    # Create the document
    body = {'title': title}
    doc = docs_service.documents().create(body=body).execute()
    doc_id = doc.get('documentId')
    
    # Parse content and retrieve cleaned text and style ranges
    cleaned_text, heading_ranges = parse_markdown_to_gdocs(content)
    
    # Request 1: Insert the full body text
    requests = [
        {
            'insertText': {
                'location': {
                    'index': 1,
                },
                'text': cleaned_text
            }
        }
    ]
    
    # Request 2+: Apply paragraph styles to header ranges
    for hr in heading_ranges:
        requests.append({
            'updateParagraphStyle': {
                'range': {
                    'startIndex': hr['startIndex'],
                    'endIndex': hr['endIndex']
                },
                'paragraphStyle': {
                    'namedStyleType': hr['style']
                },
                'fields': 'namedStyleType'
            }
        })
        
    # Execute structural updates in one batch
    docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
    
    # Make the doc shareable
    make_shareable(doc_id, docs_service, drive_service)
    
    # Get the webViewLink (shareable link)
    file_metadata = drive_service.files().get(fileId=doc_id, fields='webViewLink').execute()
    return file_metadata.get('webViewLink')
