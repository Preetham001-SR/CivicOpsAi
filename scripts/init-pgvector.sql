-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create custom types
CREATE TYPE complaint_status AS ENUM (
    'pending',
    'processing',
    'awaiting_review',
    'approved',
    'rejected',
    'completed'
);

CREATE TYPE complaint_category AS ENUM (
    'pothole',
    'broken_sign',
    'damaged_property',
    'graffiti',
    'streetlight_outage',
    'sidewalk_damage',
    'traffic_signal',
    'drainage_issue',
    'other'
);

CREATE TYPE priority_level AS ENUM (
    'low',
    'medium',
    'high',
    'critical'
);

CREATE TYPE agent_type AS ENUM (
    'intake',
    'vision',
    'speech',
    'location',
    'rag',
    'decision',
    'verification',
    'human_review'
);