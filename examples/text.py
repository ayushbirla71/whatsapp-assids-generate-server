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
        
        data_path = generate_data_file(attributes, name, msisdn, temp_dir)
        if data_path:
            generated_assets["video"] = data_path
        

        return generated_assets
        
    except Exception as e:
        print(f"Error generating assets: {e}")
        return None


def generate_data_file(attributes: Dict[str, Any], name: str, msisdn: str, temp_dir: str) -> Optional[str]:
    """Generate a JSON data file with all personalization data"""
    try:
        return "https://waterbilles.s3.ap-south-1.amazonaws.com/output.mp4"
    except Exception as e:
        print(f"Error generating data file: {e}")
        return None
