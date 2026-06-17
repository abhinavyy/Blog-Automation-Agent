import os
from typing import List, Dict, Any
from googleapiclient.discovery import build
from utils.gdocs_handler import get_google_credentials

def get_sheets_service():
    """
    Returns Google Sheets service client.
    """
    creds = get_google_credentials()
    return build('sheets', 'v4', credentials=creds)

def read_unprocessed_topics_from_sheets(sheet_id: str, range_name: str) -> List[Dict[str, Any]]:
    """
    Reads the Google Sheet and extracts rows where 'Link' or 'Blog Link' is empty.
    Assumes standard columns: Category, Topic, Updated Date, and Link.
    """
    sheets_service = get_sheets_service()
    
    # Read the values
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=range_name
    ).execute()
    
    rows = result.get('values', [])
    if not rows:
        return []

    # Clean headers to map dynamically
    headers_clean = [str(val).strip().lower() for val in rows[0]]
    
    try:
        cat_idx = headers_clean.index("category")
    except ValueError:
        cat_idx = 0
        
    try:
        topic_idx = headers_clean.index("topic")
    except ValueError:
        topic_idx = 1
        
    try:
        if "link" in headers_clean:
            link_idx = headers_clean.index("link")
        elif "blog link" in headers_clean:
            link_idx = headers_clean.index("blog link")
        else:
            link_idx = 3
    except ValueError:
        link_idx = 3

    unprocessed = []
    
    # Process from row 2 (which is index 1 of the list)
    for idx, row in enumerate(rows[1:], start=2):
        category = row[cat_idx] if len(row) > cat_idx else ""
        topic = row[topic_idx] if len(row) > topic_idx else ""
        link = row[link_idx] if len(row) > link_idx else ""
        
        if topic and (not link or str(link).strip() == ""):
            unprocessed.append({
                "category": str(category).strip(),
                "topic": str(topic).strip(),
                "row_index": idx
            })
            
    return unprocessed

def update_blog_link_in_sheets(sheet_id: str, row_index: int, blog_link: str, range_name: str = "Sheet1!A:D") -> None:
    """
    Updates the 'Link'/'Blog Link' column and 'Updated Date' column in Google Sheets.
    """
    sheets_service = get_sheets_service()
    
    # Get headers dynamically to locate correct columns
    sheet_prefix = range_name.split('!')[0] if '!' in range_name else "Sheet1"
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=f"{sheet_prefix}!1:1"
    ).execute()
    headers = result.get('values', [[]])[0]
    headers_clean = [str(h).strip().lower() for h in headers]
    
    # Find Link column
    try:
        if "link" in headers_clean:
            link_idx = headers_clean.index("link")
        elif "blog link" in headers_clean:
            link_idx = headers_clean.index("blog link")
        else:
            link_idx = 3
    except ValueError:
        link_idx = 3
        
    # Find Updated Date column
    try:
        if "updated date" in headers_clean:
            date_idx = headers_clean.index("updated date")
        else:
            date_idx = 2
    except ValueError:
        date_idx = 2

    # Map indices to column letters: 0 -> A, 1 -> B, 2 -> C, 3 -> D, etc.
    link_col = chr(65 + link_idx)
    date_col = chr(65 + date_idx)
    
    from datetime import datetime
    current_date = datetime.now().strftime("%d/%m/%Y")
    
    # Write the blog link
    sheets_service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f"{sheet_prefix}!{link_col}{row_index}",
        valueInputOption="RAW",
        body={'values': [[blog_link]]}
    ).execute()
    
    # Write the updated date
    sheets_service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f"{sheet_prefix}!{date_col}{row_index}",
        valueInputOption="RAW",
        body={'values': [[current_date]]}
    ).execute()
