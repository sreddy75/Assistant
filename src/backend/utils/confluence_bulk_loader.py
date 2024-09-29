import csv
import os
from atlassian import Confluence

class ConfluenceBulkUploader:
    def __init__(self, url, username, api_token):
        self.confluence = Confluence(
            url=url,
            username=username,
            password=api_token,
            cloud=True  # Set to False if using Confluence Server
        )
        self.page_cache = {}

    def get_or_create_page(self, space_key, title, body, parent_id=None):
        if title in self.page_cache:
            return self.page_cache[title]

        existing_page = self.confluence.get_page_by_title(space_key, title, expand='ancestors')
        if existing_page:
            self.page_cache[title] = existing_page
            return existing_page

        try:
            page = self.confluence.create_page(
                space=space_key,
                title=title,
                body=body,
                parent_id=parent_id,
                type='page'
            )
            print(f"Created page: {title}")
            self.page_cache[title] = page
            return page
        except Exception as e:
            print(f"Error creating page '{title}': {str(e)}")
            return None

    def bulk_upload_from_csv(self, space_key, csv_file, root_folder=None):
        root_id = None
        if root_folder:
            root_page = self.confluence.get_page_by_title(space_key, root_folder)
            if root_page:
                root_id = root_page['id']
            else:
                print(f"Root folder '{root_folder}' not found. Creating pages at space root.")

        with open(csv_file, 'r') as file:
            reader = csv.DictReader(file)
            hierarchy = {}
            
            # First pass: Create all pages
            for row in reader:
                title = row['title']
                body = row['content']
                parent_title = row.get('parent', '')
                
                parent_id = root_id if not parent_title else None
                if parent_title in self.page_cache:
                    parent_id = self.page_cache[parent_title]['id']
                
                page = self.get_or_create_page(space_key, title, body, parent_id)
                if page:
                    hierarchy[title] = {'page': page, 'children': []}
                    if parent_title:
                        hierarchy[parent_title]['children'].append(title)

            # Second pass: Update parent-child relationships
            for title, info in hierarchy.items():
                page = info['page']
                for child_title in info['children']:
                    child_page = hierarchy[child_title]['page']
                    if child_page['parent']['id'] != page['id']:
                        self.confluence.update_page(
                            child_page['id'],
                            child_page['title'],
                            child_page['body']['storage']['value'],
                            parent_id=page['id']
                        )
                        print(f"Updated parent for '{child_title}' to '{title}'")

def get_all_pages(self, space_key: str):
        all_pages = []
        start = 0
        limit = 50  # Adjust as needed

        while True:
            pages = self.confluence.get_all_pages_from_space(space_key, start=start, limit=limit)
            if not pages:
                break
            all_pages.extend(pages)
            start += limit

        return all_pages                        

def main():
    url = "https://kr8it.atlassian.net"
    username = "suren@kr8it.com"
    api_token = "ATATT3xFfGF0xz1K4YRXHMSEYus0W1gmetq3ulyipQDZH9pIQ2VvViaTy0HEUSYl-WDtWrTaypmmbIzvRPosK4CRKoNxyRSEURUPx3EYxm-j3j4ya27hi50XWgfpWREnDVD-nQ6j8QgPvhRenvk1ODex6tI6C4xvlSm5aly9LbHhgNTv-vONFQs=EC4F3D1A"
    space_key = "CTM"    
    root_folder = "Car Vertical"  
    
    # Use an absolute path for the CSV file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_file = os.path.join(script_dir, "car_insurance_confluence_pages.csv")

    if not os.path.exists(csv_file):
        print(f"Error: CSV file not found at {csv_file}")
        return

    uploader = ConfluenceBulkUploader(url, username, api_token)
    uploader.bulk_upload_from_csv(space_key, csv_file, root_folder)

if __name__ == "__main__":
    main()