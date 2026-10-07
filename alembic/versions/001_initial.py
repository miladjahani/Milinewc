"""initial schema

Revision ID: 001_initial
Revises: 
Create Date: 2026-10-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('username', sa.String(64), unique=True, nullable=False),
        sa.Column('display_name', sa.String(128), nullable=False),
        sa.Column('uuid', sa.String(36), unique=True, nullable=False),
        sa.Column('subscription_token', sa.String(64), unique=True, nullable=False),
        sa.Column('status', sa.String(16), server_default='active'),
        sa.Column('expires_at', sa.String(64), nullable=True),
        sa.Column('traffic_limit', sa.BigInteger(), server_default='0'),
        sa.Column('upload', sa.BigInteger(), server_default='0'),
        sa.Column('download', sa.BigInteger(), server_default='0'),
        sa.Column('device_limit', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.String(64), nullable=False),
        sa.Column('updated_at', sa.String(64), nullable=False),
        sa.Column('last_seen_at', sa.String(64), nullable=True),
    )

    op.create_table(
        'admins',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('username', sa.String(64), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(256), nullable=False),
        sa.Column('role', sa.String(32), server_default='admin'),
        sa.Column('created_at', sa.String(64), nullable=False),
    )

    op.create_table(
        'nodes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('protocol', sa.String(32), nullable=False),
        sa.Column('address', sa.String(255), nullable=False),
        sa.Column('port', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(64), nullable=True),
        sa.Column('password', sa.String(255), nullable=True),
        sa.Column('path', sa.String(255), server_default='/'),
        sa.Column('host', sa.String(255), nullable=True),
        sa.Column('sni', sa.String(255), nullable=True),
        sa.Column('alpn', sa.String(64), nullable=True),
        sa.Column('network', sa.String(32), server_default='ws'),
        sa.Column('tls', sa.Integer(), server_default='1'),
        sa.Column('proxyip', sa.String(255), nullable=True),
        sa.Column('region', sa.String(32), server_default='US'),
        sa.Column('enabled', sa.Integer(), server_default='1'),
    )

    op.create_table(
        'shadowsocks_credentials',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('method', sa.String(64), nullable=False),
        sa.Column('password', sa.String(255), nullable=False),
        sa.Column('server', sa.String(255), nullable=True),
        sa.Column('port', sa.Integer(), nullable=False),
        sa.Column('udp', sa.Integer(), server_default='1'),
        sa.Column('enabled', sa.Integer(), server_default='1'),
    )

def downgrade():
    op.drop_table('shadowsocks_credentials')
    op.drop_table('nodes')
    op.drop_table('admins')
    op.drop_table('users')
