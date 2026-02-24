from dotenv import load_dotenv
import os

load_dotenv()

token = os.getenv('NOTION_TOKEN', 'NOT FOUND')
page_id = os.getenv('NOTION_PARENT_PAGE_ID', 'NOT FOUND')

print(f'Token starts with: {token[:10]}...')
print(f'Token length: {len(token)}')
print(f'Page ID length: {len(page_id)} (should be 32)')
print(f'Page ID valid hex: {all(c in "0123456789abcdef-" for c in page_id)}')