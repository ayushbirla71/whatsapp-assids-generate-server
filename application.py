#!/usr/bin/env python3
"""
AWS Elastic Beanstalk entry point for WhatsApp Asset Generation Server
This file is required for EB deployment
"""

from main import app

# AWS Elastic Beanstalk looks for an 'application' object
application = app

if __name__ == "__main__":
    # For local testing
    import uvicorn
    uvicorn.run(application, host="0.0.0.0", port=8000)
