# Sample Asset Generation File
# This file demonstrates how to create an asset generation module
# that can be stored in the database and executed dynamically

import os
from PIL import Image, ImageDraw, ImageFont
import json
from typing import Dict, Any, Optional

def generate_asset(
    attributes: Dict[str, Any], 
    name: str, 
    msisdn: str, 
    temp_dir: str
) -> Optional[Dict[str, str]]:
    """
    Generate personalized assets for a WhatsApp campaign audience member
    
    Args:
        attributes: Custom attributes from campaign_audience.attributes
        name: Audience member name
        msisdn: Phone number
        temp_dir: Temporary directory to save generated files
        
    Returns:
        Dictionary with asset types and their file paths
        Example: {"image": "/path/to/image.png", "video": "/path/to/video.mp4"}
    """
    
    try:
        generated_assets = {}
        
        # Example 1: Generate a personalized image
        image_path = generate_personalized_image(attributes, name, temp_dir)
        if image_path:
            generated_assets["image"] = image_path
        
        # Example 2: Generate a personalized text file (could be used for dynamic content)
        text_path = generate_personalized_text(attributes, name, msisdn, temp_dir)
        if text_path:
            generated_assets["text"] = text_path
        
        # Example 3: Generate JSON data file
        data_path = generate_data_file(attributes, name, msisdn, temp_dir)
        if data_path:
            generated_assets["data"] = data_path
        
        return generated_assets
        
    except Exception as e:
        print(f"Error generating assets: {e}")
        return None

def generate_personalized_image(attributes: Dict[str, Any], name: str, temp_dir: str) -> Optional[str]:
    """Generate a personalized image with the user's name"""
    try:
        # Create a simple image with text
        width, height = 800, 400
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)
        
        # Try to use a default font, fallback to default if not available
        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except:
            font = ImageFont.load_default()
        
        # Get personalized text from attributes or use default
        greeting = attributes.get('greeting', 'Hello')
        offer = attributes.get('offer', 'Special Offer Just for You!')
        
        # Draw text on image
        text_lines = [
            f"{greeting} {name}!",
            offer,
            "Don't miss out on this exclusive deal!"
        ]
        
        y_offset = 50
        for line in text_lines:
            # Calculate text position to center it
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            
            draw.text((x, y_offset), line, fill='black', font=font)
            y_offset += 80
        
        # Add a colored rectangle as decoration
        draw.rectangle([50, height-100, width-50, height-50], fill='blue')
        draw.text((60, height-85), "Exclusive Offer", fill='white', font=font)
        
        # Save the image
        image_path = os.path.join(temp_dir, f"personalized_image_{name.replace(' ', '_')}.png")
        image.save(image_path)
        
        return image_path
        
    except Exception as e:
        print(f"Error generating personalized image: {e}")
        return None

def generate_personalized_text(attributes: Dict[str, Any], name: str, msisdn: str, temp_dir: str) -> Optional[str]:
    """Generate personalized text content"""
    try:
        # Create personalized message content
        product = attributes.get('product', 'our amazing product')
        discount = attributes.get('discount', '20%')
        expiry_date = attributes.get('expiry_date', '31st December')
        
        message_content = f"""
Dear {name},

We have an exclusive offer just for you!

Get {discount} off on {product} - but hurry, this offer expires on {expiry_date}!

Your personal discount code: {name.upper()[:3]}{msisdn[-4:]}

Visit our store or call us to claim your discount.

Best regards,
The Marketing Team
        """.strip()
        
        # Save to file
        text_path = os.path.join(temp_dir, f"personalized_message_{name.replace(' ', '_')}.txt")
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(message_content)
        
        return text_path
        
    except Exception as e:
        print(f"Error generating personalized text: {e}")
        return None

def generate_data_file(attributes: Dict[str, Any], name: str, msisdn: str, temp_dir: str) -> Optional[str]:
    """Generate a JSON data file with all personalization data"""
    try:
        # Compile all data into a structured format
        data = {
            "audience_member": {
                "name": name,
                "msisdn": msisdn
            },
            "personalization": attributes,
            "generated_content": {
                "greeting": attributes.get('greeting', 'Hello'),
                "offer": attributes.get('offer', 'Special Offer Just for You!'),
                "discount_code": f"{name.upper()[:3]}{msisdn[-4:]}",
                "product": attributes.get('product', 'our amazing product'),
                "discount": attributes.get('discount', '20%'),
                "expiry_date": attributes.get('expiry_date', '31st December')
            },
            "metadata": {
                "generated_at": "2024-01-01T00:00:00Z",  # This would be actual timestamp
                "template_version": "1.0"
            }
        }
        
        # Save to JSON file
        data_path = os.path.join(temp_dir, f"personalization_data_{name.replace(' ', '_')}.json")
        with open(data_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return data_path
        
    except Exception as e:
        print(f"Error generating data file: {e}")
        return None

# Additional utility functions that can be used in asset generation

def create_qr_code(data: str, temp_dir: str, filename: str) -> Optional[str]:
    """Generate QR code (requires qrcode library)"""
    try:
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        qr_path = os.path.join(temp_dir, f"{filename}.png")
        img.save(qr_path)
        return qr_path
    except ImportError:
        print("qrcode library not installed")
        return None
    except Exception as e:
        print(f"Error generating QR code: {e}")
        return None

def resize_image(image_path: str, max_width: int, max_height: int) -> bool:
    """Resize image to fit within max dimensions while maintaining aspect ratio"""
    try:
        with Image.open(image_path) as img:
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            img.save(image_path)
        return True
    except Exception as e:
        print(f"Error resizing image: {e}")
        return False
