"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ENUM as PG_ENUM
import uuid

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types idempotently
    op.execute("DO $$ BEGIN CREATE TYPE complaint_status AS ENUM ('pending', 'processing', 'awaiting_review', 'approved', 'rejected', 'completed'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE complaint_category AS ENUM ('pothole', 'broken_sign', 'damaged_property', 'graffiti', 'streetlight_outage', 'sidewalk_damage', 'traffic_signal', 'drainage_issue', 'other'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE priority_level AS ENUM ('low', 'medium', 'high', 'critical'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE agent_type AS ENUM ('intake', 'vision', 'speech', 'location', 'rag', 'decision', 'verification', 'human_review'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    
    # Create complaints table
    op.create_table(
        'complaints',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('status', PG_ENUM('pending', 'processing', 'awaiting_review', 'approved', 'rejected', 'completed', name='complaint_status', create_type=False), nullable=False, default='pending'),
        sa.Column('category', PG_ENUM('pothole', 'broken_sign', 'damaged_property', 'graffiti', 'streetlight_outage', 'sidewalk_damage', 'traffic_signal', 'drainage_issue', 'other', name='complaint_category', create_type=False), nullable=True),
        sa.Column('priority', PG_ENUM('low', 'medium', 'high', 'critical', name='priority_level', create_type=False), nullable=True),
        sa.Column('text_description', sa.Text(), nullable=True),
        sa.Column('photo_url', sa.String(500), nullable=True),
        sa.Column('audio_url', sa.String(500), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('address', sa.String(500), nullable=True),
        sa.Column('vision_analysis', sa.JSON(), nullable=True),
        sa.Column('speech_transcript', sa.Text(), nullable=True),
        sa.Column('location_details', sa.JSON(), nullable=True),
        sa.Column('rag_context', sa.JSON(), nullable=True),
        sa.Column('decision', sa.JSON(), nullable=True),
        sa.Column('verification', sa.JSON(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('work_order_id', sa.String(100), nullable=True),
        sa.Column('work_order_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )
    
    op.create_index('ix_complaints_location', 'complaints', ['latitude', 'longitude'])
    op.create_index('ix_complaints_status', 'complaints', ['status'])
    op.create_index('ix_complaints_created_at', 'complaints', ['created_at'])
    
    # Create agent_logs table
    op.create_table(
        'agent_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('complaint_id', UUID(as_uuid=True), sa.ForeignKey('complaints.id', ondelete='CASCADE'), nullable=False),
        sa.Column('agent_type', PG_ENUM('intake', 'vision', 'speech', 'location', 'rag', 'decision', 'verification', 'human_review', name='agent_type', create_type=False), nullable=False),
        sa.Column('input_data', sa.JSON(), nullable=False),
        sa.Column('output_data', sa.JSON(), nullable=False),
        sa.Column('execution_time_ms', sa.Integer(), nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('trace_id', sa.String(100), nullable=True),
        sa.Column('span_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.now()),
    )
    
    op.create_index('ix_agent_logs_complaint_id', 'agent_logs', ['complaint_id'])
    op.create_index('ix_agent_logs_agent_type', 'agent_logs', ['agent_type'])
    
    # Create human_reviews table
    op.create_table(
        'human_reviews',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('complaint_id', UUID(as_uuid=True), sa.ForeignKey('complaints.id', ondelete='CASCADE'), nullable=False),
        sa.Column('reviewer_id', sa.String(100), nullable=False),
        sa.Column('decision', sa.String(50), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('modified_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )
    
    op.create_index('ix_human_reviews_complaint_id', 'human_reviews', ['complaint_id'])
    
    # Create rag_documents table
    op.create_table(
        'rag_documents',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', sa.ARRAY(sa.Float()), nullable=False),  # pgvector will be added via extension
        sa.Column('metadata', sa.JSON(), nullable=False, default={}),
        sa.Column('source', sa.String(200), nullable=False),
        sa.Column('category', PG_ENUM('pothole', 'broken_sign', 'damaged_property', 'graffiti', 'streetlight_outage', 'sidewalk_damage', 'traffic_signal', 'drainage_issue', 'other', name='complaint_category', create_type=False), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.now()),
    )
    
    op.create_index('ix_rag_documents_category', 'rag_documents', ['category'])
    op.create_index('ix_rag_documents_source', 'rag_documents', ['source'])
    
    # Create work_orders table
    op.create_table(
        'work_orders',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('complaint_id', UUID(as_uuid=True), sa.ForeignKey('complaints.id', ondelete='CASCADE'), nullable=False),
        sa.Column('work_order_number', sa.String(100), nullable=False, unique=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', PG_ENUM('pothole', 'broken_sign', 'damaged_property', 'graffiti', 'streetlight_outage', 'sidewalk_damage', 'traffic_signal', 'drainage_issue', 'other', name='complaint_category', create_type=False), nullable=False),
        sa.Column('priority', PG_ENUM('low', 'medium', 'high', 'critical', name='priority_level', create_type=False), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('address', sa.String(500), nullable=True),
        sa.Column('assigned_department', sa.String(200), nullable=True),
        sa.Column('estimated_cost', sa.Float(), nullable=True),
        sa.Column('estimated_duration_days', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='open'),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )
    
    op.create_index('ix_work_orders_complaint_id', 'work_orders', ['complaint_id'])
    op.create_index('ix_work_orders_status', 'work_orders', ['status'])


def downgrade() -> None:
    op.drop_table('work_orders')
    op.drop_table('rag_documents')
    op.drop_table('human_reviews')
    op.drop_table('agent_logs')
    op.drop_table('complaints')
    
    op.execute("DROP TYPE agent_type")
    op.execute("DROP TYPE priority_level")
    op.execute("DROP TYPE complaint_category")
    op.execute("DROP TYPE complaint_status")