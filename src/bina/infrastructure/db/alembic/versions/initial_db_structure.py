"""Initial database structure with HNSW index for embeddings.

Revision ID: initial_db_structure
Revises: 
Create Date: 2026-09-18

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'initial_db_structure'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create bina_users table
    op.create_table('bina_users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('language', sa.String(length=3), nullable=False),
        sa.Column('role', sa.Enum('user', 'realtor', 'admin', name='userrole'), nullable=False),
        sa.Column('balance', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('subscription_tier', sa.Enum('free', 'nomad', 'family', 'realtor', name='subscriptiontier'), nullable=False),
        sa.Column('subscription_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_id')
    )
    op.create_index('ix_bina_users_telegram_id', 'bina_users', ['telegram_id'], unique=False)

    # Create bina_districts table
    op.create_table('bina_districts',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name_ru', sa.String(), nullable=False),
        sa.Column('name_ka', sa.String(), nullable=False),
        sa.Column('name_en', sa.String(), nullable=False),
        sa.Column('center_coordinates', sa.String(), nullable=True),
        sa.Column('avg_price_per_m2', sa.Numeric(), nullable=False),
        sa.Column('safety_score', sa.Integer(), nullable=False),
        sa.Column('infrastructure_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create bina_listings table
    op.create_table('bina_listings',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('source_id', sa.String(), nullable=False),
        sa.Column('source_name', sa.String(), nullable=False),
        sa.Column('title_ru', sa.String(), nullable=False),
        sa.Column('title_ka', sa.String(), nullable=False),
        sa.Column('description_ru', sa.Text(), nullable=False),
        sa.Column('description_ka', sa.Text(), nullable=False),
        sa.Column('price', sa.Numeric(), nullable=False),
        sa.Column('currency', sa.String(), nullable=False),
        sa.Column('district_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('rooms', sa.Integer(), nullable=False),
        sa.Column('area', sa.Numeric(), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=False),
        sa.Column('fraud_score', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('active', 'sold', 'archived', name='listingstatus'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['district_id'], ['bina_districts.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_id')
    )
    
    # Create composite index for listings
    op.create_index('ix_bina_listings_district_status_price', 'bina_listings', 
                   ['district_id', 'status', 'price'], unique=False)
    
    # Create GIN index for full-text search
    op.execute("""
        CREATE INDEX ix_bina_listings_search_vector 
        ON bina_listings 
        USING gin(to_tsvector('russian', title_ru || ' ' || description_ru));
    """)

    # Create bina_embeddings table
    op.create_table('bina_embeddings',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('listing_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('vector', Vector(1536), nullable=False),
        sa.Column('model_name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['listing_id'], ['bina_listings.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create HNSW index for vector similarity search
    op.execute("""
        CREATE INDEX ix_bina_embeddings_vector_hnsw 
        ON bina_embeddings 
        USING hnsw (vector vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
    """)
    
    # EXPLAIN ANALYZE comment for the HNSW index
    # This index enables efficient cosine similarity searches on embedding vectors
    # Typical query: SELECT listing_id FROM bina_embeddings ORDER BY vector <=> ? LIMIT 10
    # With this HNSW index, such queries should execute in milliseconds even with millions of vectors

    # Create bina_favorites table
    op.create_table('bina_favorites',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('listing_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['listing_id'], ['bina_listings.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['bina_users.id'], ),
        sa.PrimaryKeyConstraint('user_id', 'listing_id'),
        sa.UniqueConstraint('user_id', 'listing_id', name='uq_favorites_user_listing')
    )

    # Create bina_payments table
    op.create_table('bina_payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amount', sa.Numeric(), nullable=False),
        sa.Column('currency', sa.String(), nullable=False),
        sa.Column('provider', sa.Enum('telegram_stars', 'stripe', name='paymentprovider'), nullable=False),
        sa.Column('provider_payment_id', sa.String(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'success', 'failed', name='paymentstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['bina_users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider_payment_id')
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('bina_payments')
    op.drop_table('bina_favorites')
    op.drop_table('bina_embeddings')
    op.drop_table('bina_listings')
    op.drop_table('bina_districts')
    op.drop_table('bina_users')
    
    # Drop enums
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("DROP TYPE IF EXISTS subscriptiontier")
    op.execute("DROP TYPE IF EXISTS listingstatus")
    op.execute("DROP TYPE IF EXISTS paymentprovider")
    op.execute("DROP TYPE IF EXISTS paymentstatus")