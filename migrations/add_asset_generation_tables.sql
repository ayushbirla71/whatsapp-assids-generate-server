-- Migration script to add asset generation functionality to existing WhatsApp server database
-- Run this script on your existing database to add the new tables and columns

-- Add new enum types for asset generation (with conflict handling)
DO $$
BEGIN
    -- Create asset_generation_status enum if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'asset_generation_status') THEN
        CREATE TYPE asset_generation_status AS ENUM ('pending', 'processing', 'generated', 'failed');
    END IF;

    -- Create or update message_status_extended enum
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'message_status_extended') THEN
        CREATE TYPE message_status_extended AS ENUM ('pending', 'asset_generating', 'asset_generated', 'ready_to_send', 'sent', 'delivered', 'read', 'failed');
    ELSE
        -- Add missing values to existing enum
        IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'asset_generating' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'message_status_extended')) THEN
            ALTER TYPE message_status_extended ADD VALUE 'asset_generating';
        END IF;

        IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'asset_generated' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'message_status_extended')) THEN
            ALTER TYPE message_status_extended ADD VALUE 'asset_generated';
        END IF;

        IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'ready_to_send' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'message_status_extended')) THEN
            ALTER TYPE message_status_extended ADD VALUE 'ready_to_send';
        END IF;
    END IF;

    -- Add missing values to campaign_status enum
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'asset_generation' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'campaign_status')) THEN
        ALTER TYPE campaign_status ADD VALUE 'asset_generation';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'asset_generated' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'campaign_status')) THEN
        ALTER TYPE campaign_status ADD VALUE 'asset_generated';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'ready_to_launch' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'campaign_status')) THEN
        ALTER TYPE campaign_status ADD VALUE 'ready_to_launch';
    END IF;
END $$;

-- Create asset_generate_files table
CREATE TABLE asset_generate_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id UUID NOT NULL REFERENCES templates(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    file_content TEXT NOT NULL,
    description TEXT,
    version VARCHAR(50) DEFAULT '1.0',
    is_active BOOLEAN DEFAULT true,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Constraints
    CONSTRAINT asset_files_template_filename_unique UNIQUE (template_id, file_name)
);

-- Add asset generation columns to campaigns table
ALTER TABLE campaigns
ADD COLUMN asset_generation_started_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN asset_generation_completed_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN asset_generation_status asset_generation_status,
ADD COLUMN asset_generation_retry_count INTEGER DEFAULT 0,
ADD COLUMN asset_generation_last_error TEXT,
ADD COLUMN asset_generation_progress JSONB DEFAULT '{}';

-- Update campaign_status enum to include new statuses
ALTER TYPE campaign_status ADD VALUE 'asset_generation';
ALTER TYPE campaign_status ADD VALUE 'asset_generated';
ALTER TYPE campaign_status ADD VALUE 'ready_to_launch';

-- Add asset generation columns to campaign_audience table
ALTER TABLE campaign_audience
ADD COLUMN asset_generation_status asset_generation_status,
ADD COLUMN generated_asset_urls JSONB DEFAULT '{}',
ADD COLUMN asset_generation_retry_count INTEGER DEFAULT 0,
ADD COLUMN asset_generation_last_error TEXT,
ADD COLUMN asset_generation_started_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN asset_generation_completed_at TIMESTAMP WITH TIME ZONE;

-- Update message_status to use extended enum (this requires careful handling)
-- First, add a new column with the extended enum
ALTER TABLE campaign_audience 
ADD COLUMN message_status_new message_status_extended DEFAULT 'pending';

-- Copy existing data
UPDATE campaign_audience 
SET message_status_new = CASE 
    WHEN message_status = 'pending' THEN 'pending'::message_status_extended
    WHEN message_status = 'sent' THEN 'sent'::message_status_extended
    WHEN message_status = 'delivered' THEN 'delivered'::message_status_extended
    WHEN message_status = 'read' THEN 'read'::message_status_extended
    WHEN message_status = 'failed' THEN 'failed'::message_status_extended
    ELSE 'pending'::message_status_extended
END;

-- Drop the old column and rename the new one
ALTER TABLE campaign_audience DROP COLUMN message_status;
ALTER TABLE campaign_audience RENAME COLUMN message_status_new TO message_status;

-- Create indexes for better performance
CREATE INDEX idx_asset_generate_files_template_id ON asset_generate_files(template_id);
CREATE INDEX idx_asset_generate_files_is_active ON asset_generate_files(is_active);
CREATE INDEX idx_campaigns_asset_generation_status ON campaigns(asset_generation_status);
CREATE INDEX idx_campaign_audience_asset_generation_status ON campaign_audience(asset_generation_status);
CREATE INDEX idx_campaign_audience_message_status_extended ON campaign_audience(message_status);

-- Create trigger for updated_at on asset_generate_files
CREATE TRIGGER update_asset_generate_files_updated_at 
    BEFORE UPDATE ON asset_generate_files
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert sample asset generation file
INSERT INTO asset_generate_files (template_id, file_name, file_content, description, created_by)
SELECT 
    t.id,
    'sample_image_generator.py',
    '# Sample Asset Generation File
import os
from PIL import Image, ImageDraw, ImageFont
import json

def generate_asset(attributes, name, msisdn, temp_dir):
    """Generate personalized image asset"""
    try:
        # Create personalized image
        width, height = 800, 400
        image = Image.new("RGB", (width, height), color="white")
        draw = ImageDraw.Draw(image)
        
        # Add personalized text
        greeting = attributes.get("greeting", "Hello")
        text = f"{greeting} {name}!"
        
        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except:
            font = ImageFont.load_default()
        
        # Center the text
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) // 2
        y = height // 2 - 20
        
        draw.text((x, y), text, fill="black", font=font)
        
        # Save image
        image_path = os.path.join(temp_dir, f"personalized_{name.replace('' '', ''_'')}.png")
        image.save(image_path)
        
        return {"image": image_path}
    except Exception as e:
        print(f"Error: {e}")
        return None',
    'Sample asset generation file for creating personalized images',
    (SELECT id FROM users WHERE role = 'super_admin' LIMIT 1)
FROM templates t 
WHERE t.category = 'MARKETING' 
LIMIT 1;

-- Add comments to tables
COMMENT ON TABLE asset_generate_files IS 'Stores Python code files for generating personalized assets';
COMMENT ON COLUMN asset_generate_files.file_content IS 'Python code that implements generate_asset function';
COMMENT ON COLUMN campaigns.asset_generation_status IS 'Status of asset generation process for the campaign';
COMMENT ON COLUMN campaign_audience.generated_asset_urls IS 'JSON object containing URLs of generated assets (e.g., {"image": "s3://...", "video": "s3://..."})';

-- Grant permissions (adjust as needed for your setup)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON asset_generate_files TO your_app_user;
-- GRANT USAGE ON SEQUENCE asset_generate_files_id_seq TO your_app_user;
