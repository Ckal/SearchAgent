# prompt: agent.run("Add the results of scraping: https://www.amazon.de/Amazon-Cola-24-330ml/dp/B0B2QFB69F/ref=sr_1_1_ffob_sspa?dib=eyJ2IjoiMSJ9.Ammc6GrHRevDKBSZX9_vNS5j3Kc1ZW2R4jISx9htSBAc0WWFC1xX5qnohoEQjmvNqQyWIr6hnMbFad3QuwPMVG8F_nZbwnpBcHL89OZsU2XzkSha-clTmgJLUUh7Z96_98HOe9hOif82mXyrL7ZTnbygPSbm-t6FDAfslLesKfij79QL7-a2RSOKVPcJRFR1DLUamaHfmhyN5c_rujFjb2X1rQSXg6NWCnOdgU2r1gzEa54bU8bxeQnX-vMsRMGEw4entZYP_Oh85pEImPU_lS2Awqr-sG_RgaV0Wuzfmdw.XA9kTWHZQvmhT2BoQWxRNix2TJe8EoeyjiSoQtFx1yY&dib_tag=se&keywords=Cola&qid=1738167189&rdc=1&sr=8-1-spons&sp_csd=d2lkZ2V0TmFtZT1zcF9hdGY&th=1 to a csv file")
#!pip install -q smolagents transformers sentence_transformers gradio  
from smolagents import CodeAgent, HfApiModel, tool
import requests
from bs4 import BeautifulSoup
import pandas as pd
import gradio as gr
from typing import List, Dict, Optional
import time
import random
import re
from concurrent.futures import ThreadPoolExecutor
import json
 

import pandas as pd
####
####
####
@tool
def amazon_scraper(keyword: str, mandatory_columns: List[str] = None, max_products: int = 10) -> Dict:
    """
    Enhanced Amazon scraper that gets both listing and detailed product information.

    Args:
        keyword: Search term for Amazon products
        mandatory_columns: List of specific attributes to always include
        max_products: Maximum number of products to scrape (default: 10)

    Returns:
        Dictionary containing list of products and their details, plus column names
    """
    if mandatory_columns is None:
        mandatory_columns = ['title', 'price', 'rating', 'reviews']

    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/VERSION Safari/537.36",
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }

    search_url = f"https://www.amazon.com/s?k={keyword.replace(' ', '+')}"

    try:
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        items = soup.find_all('div', attrs={'data-component-type': 's-search-result'})

        if not items:
            return {'error': 'No products found for the given search term'}

        products = []
        for item in items[:max_products]:
            try:
                product = {}

                # Basic information from search results div data-cy="title-recipe"
                # here I want to filter for : 
                title_elem = item.find('div', class_="title-instructions-style")
                product['title'] = title_elem.text.strip() if title_elem else 'N/A'

                price_elem = item.find('span', class_='a-offscreen')
                product['price'] = price_elem.text.strip() if price_elem else 'N/A'

                rating_elem = item.find('span', class_='a-icon-alt')
                product['rating'] = rating_elem.text.split(' ')[0] if rating_elem else 'N/A'

                reviews_elem = item.find('span', {'class': 'a-size-base', 'dir': 'auto'})
                product['reviews'] = reviews_elem.text.strip() if reviews_elem else '0'

                # Get product URL
                url_elem = item.find('a', class_='a-link-normal s-no-outline')
                if url_elem and 'href' in url_elem.attrs:
                    product_url = 'https://www.amazon.com' + url_elem['href']
                    product['url'] = product_url

                    # Scrape detailed information
                    details = scrape_product_details(product_url, headers)
                    product.update(details)

                products.append(product)

            except Exception as e:
                print(f"Error processing item: {str(e)}")
                continue

        if not products:
            return {'error': 'Failed to extract product information'}

        return {'products': products, 'columns': list(products[0].keys())}

    except requests.RequestException as e:
        return {'error': f'Network error: {str(e)}'}
    except Exception as e:
        return {'error': f'Unexpected error: {str(e)}'}


  
from typing import Optional, Dict
import requests
from bs4 import BeautifulSoup
from smolagents import tool  # Ensure you import @tool

@tool
def scrape_product_details(url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Scrapes product details from an Amazon product page.

    Args:
        url: The URL of the Amazon product page to scrape.
        headers: HTTP headers to include in the request. Defaults to None.

    Returns:
        Dict[str, str]: A dictionary containing:
            - 'title': Product title
            - 'price': Product price
            - 'description': Product description
            - 'bullet_points': Bullet point features (comma-separated string)
            - 'average_rating': Customer rating
            - 'total_reviews': Number of reviews
            - 'image_link': URL of the main product image
    """
    if headers is None:
        headers = {
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/VERSION Safari/537.36"
        }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return {'error': f'Failed to retrieve the page. Status code: {response.status_code}'}

    soup = BeautifulSoup(response.content, 'html.parser')

    # Extract the product title
    product_title = soup.find('span', {'id': 'productTitle'})
    product_title = product_title.get_text(strip=True) if product_title else 'Title not found'

    # Extract the product price
    product_price = soup.find('span', {'class': 'a-price-whole'})
    product_price = product_price.get_text(strip=True) if product_price else 'Price not found'

    # Extract the product description
    product_description = soup.find('div', {'id': 'productDescription'})
    product_description = product_description.get_text(strip=True) if product_description else 'Description not found'

    # Extract bullet points
    bullet_points = []
    bullet_section = soup.find('ul', {'class': 'a-unordered-list a-vertical a-spacing-mini'})
    if bullet_section:
        for li in bullet_section.find_all('li'):
            bullet = li.find('span', {'class': 'a-list-item'})
            if bullet:
                bullet_points.append(bullet.get_text(strip=True))
    bullet_points_text = ', '.join(bullet_points) if bullet_points else 'Bullet points not found'

    # Extract average customer rating
    average_rating = soup.find('span', {'class': 'a-icon-alt'})
    average_rating = average_rating.get_text(strip=True) if average_rating else 'Average rating not found'

    # Extract total number of customer reviews
    total_reviews = soup.find('span', {'id': 'acrCustomerReviewText'})
    total_reviews = total_reviews.get_text(strip=True) if total_reviews else 'Total reviews not found'

    # Extract the main image link
    image_tag = soup.find('img', {'id': 'landingImage'})
    image_link = image_tag['src'] if image_tag else 'Image link not found'

    return {
        'title': product_title,
        'price': product_price,
        'description': product_description,
        'bullet_points': bullet_points_text,
        'average_rating': average_rating,
        'total_reviews': total_reviews,
        'image_link': image_link
    }


###
###

model = HfApiModel()
agent = CodeAgent(
    tools=[amazon_scraper],
    model=model,
    additional_authorized_imports=['requests', 'bs4', 'pandas', 'gradio', 'concurrent.futures', 'csv', 'json']
)

# Assuming the agent.run call returns a dictionary with 'products' key
#####
#####
##
import gradio as gr
import pandas as pd
from typing import Dict, List, Tuple, Union
from smolagents import CodeAgent, HfApiModel, tool

def process_agent_response(response: Union[Dict, List, str]) -> Tuple[pd.DataFrame, str]:
    """
    Process the agent's response and convert it to a DataFrame
    Returns DataFrame and error message (if any)
    """
    def extract_products_from_response(resp):
        """Helper function to extract product data from various response formats"""
        if isinstance(resp, list):
            # Response is already a list of products
            return resp
        elif isinstance(resp, dict):
            # Check if it's wrapped in a 'products' key
            if 'products' in resp:
                return resp['products']
            # Check if it's a single product
            elif 'title' in resp:
                return [resp]
            elif 'error' in resp:
                return None
        elif isinstance(resp, str):
            try:
                # Try to parse the string response
                import ast
                # Remove common prefixes
                if "Final answer:" in resp:
                    resp = resp.split("Final answer:", 1)[1].strip()
                elif "Out - Final answer:" in resp:
                    resp = resp.split("Out - Final answer:", 1)[1].strip()
                
                parsed = ast.literal_eval(resp)
                # Recursively process the parsed result
                return extract_products_from_response(parsed)
            except:
                pass
        return None

    try:
        products = extract_products_from_response(response)
        
        if products is None:
            return pd.DataFrame(), "No valid product data found"
        
        # Convert to DataFrame
        df = pd.DataFrame(products)
        
        # Clean up column names
        df.columns = [col.lower().strip() for col in df.columns]
        
        return df, ""
            
    except Exception as e:
        return pd.DataFrame(), f"Error processing data: {str(e)}"

def search_products(keyword: str, max_products: int) -> Tuple[pd.DataFrame, str, str]:
    """
    Search for products and return results as a DataFrame
    Returns: (DataFrame, status message, error message)
    """
    try:
        result = agent.run(f'Show me details for {max_products} amazon products with keyword: {keyword}. Return a product-json with resp["products"]')
        df, error_msg = process_agent_response(result)
        
        if not df.empty:
            # Select and reorder relevant columns, using lowercase names
            display_columns = [
                'title', 'price', 'rating', 'reviews', 'description', 
                'bullet_points', 'average_rating', 'total_reviews'
            ]
            # Filter for columns that actually exist in the DataFrame
            available_columns = [col for col in display_columns if col in df.columns]
            df = df[available_columns]
            
            # Clean up the display
            if 'price' in df.columns:
                df['price'] = df['price'].apply(lambda x: f"${str(x).strip('.')}")
            
            # Truncate long text fields for better display
            if 'description' in df.columns:
                df['description'] = df['description'].apply(lambda x: x[:200] + '...' if len(x) > 200 else x)
            if 'bullet_points' in df.columns:
                df['bullet_points'] = df['bullet_points'].apply(lambda x: x[:200] + '...' if len(x) > 200 else x)
            
            status_msg = f"Found {len(df)} products"
            return df, status_msg, ""
        else:
            return df, "", error_msg or "No products found"
            
    except Exception as e:
        return pd.DataFrame(), "", f"Search error: {str(e)}"

def answer_product_question(df: pd.DataFrame, question: str) -> str:
    """
    Answer questions about the products using the agent
    """
    if df.empty:
        return "Please search for products first before asking questions."
    
    try:
        # Convert DataFrame to a more readable format for the agent
        products_context = df.to_dict('records')
        
        prompt = f"""Based on these products:
{products_context}

Question: {question}

Please provide a clear and concise answer using only the information available in the product data."""
        
        response = agent.run(prompt)
        
        # Handle different response formats
        if isinstance(response, dict):
            return str(response)
        return response
        
    except Exception as e:
        return f"Error processing question: {str(e)}"

def create_interface() -> gr.Interface:
    """
    Create the Gradio interface with search and Q&A functionality
    """
    with gr.Blocks(title="Amazon Product Search & Q&A") as interface:
        gr.Markdown("# Amazon Product Search and Q&A System")
        
        # Status message for feedback
        status_msg = gr.Markdown("")
        
        with gr.Row():
            with gr.Column():
                keyword_input = gr.Textbox(
                    label="Product Keyword or Name",
                    placeholder="Enter product keyword...",
                    scale=3
                )
                max_products = gr.Slider(
                    minimum=1,
                    maximum=10,
                    value=5,
                    step=1,
                    label="Number of Products",
                )
                search_button = gr.Button("Search Products", variant="primary")
            
            with gr.Column():
                question_input = gr.Textbox(
                    label="Ask about the products",
                    placeholder="Enter your question about the products...",
                    scale=3
                )
                ask_button = gr.Button("Ask Question", variant="secondary")

        # Output components
        with gr.Row():
            with gr.Column(scale=2):
                product_table = gr.Dataframe(
                    label="Product Search Results",
                    interactive=False,
                    wrap=True
                )
            with gr.Column(scale=1):
                answer_output = gr.Markdown(
                    label="Answer to Your Question"
                )

        # Store DataFrame state
        df_state = gr.State(pd.DataFrame())

        def on_search(keyword: str, max_products: int) -> Tuple[pd.DataFrame, pd.DataFrame, str]:
            # TODO add thinking in an output
            df, status, error = search_products(keyword, max_products)
            message = error if error else status
            return df, df, gr.Markdown(message)

        def on_question(df: pd.DataFrame, question: str) -> str:
            # TODO add thinking in an output
            return answer_product_question(df, question)

        # Connect components
        search_button.click(
            fn=on_search,
            inputs=[keyword_input, max_products],
            outputs=[product_table, df_state, status_msg]
        )
        
        ask_button.click(
            fn=on_question,
            inputs=[df_state, question_input],
            outputs=answer_output
        )

    return interface

def main():
    # Create and launch the interface
    interface = create_interface()
    interface.launch(
        debug=True,
        server_name="0.0.0.0",
        server_port=7860
    )

if __name__ == "__main__":
    main()
