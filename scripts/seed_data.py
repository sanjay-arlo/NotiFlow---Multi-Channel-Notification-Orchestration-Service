#!/usr/bin/env python3
"""
Script to seed the database with sample data for development and testing.
"""

import asyncio
import sys
from datetime import datetime, time
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import generate_api_key
from app.db.session import get_async_session
from app.db.models.tenant import Tenant
from app.db.models.user import User
from app.db.models.template import Template
from app.db.models.webhook_config import WebhookConfig
from app.repositories.tenant_repo import TenantRepository
from app.repositories.user_repo import UserRepository
from app.repositories.template_repo import TemplateRepository
from app.repositories.webhook_config_repo import WebhookConfigRepository


async def create_sample_tenant(tenant_repo: TenantRepository) -> Tenant:
    """Create a sample tenant for testing."""
    api_key = generate_api_key()
    
    tenant_data = {
        "name": "NotiFlow Demo",
        "api_key_hash": api_key["hash"],
        "api_key_prefix": api_key["prefix"],
        "is_active": True,
        "rate_limit": 1000
    }
    
    tenant = await tenant_repo.create(tenant_data)
    print(f"✅ Created tenant: {tenant.name}")
    print(f"   API Key: {api_key['full']}")
    
    return tenant


async def create_sample_users(user_repo: UserRepository, tenant_id: str) -> list[User]:
    """Create sample users for testing."""
    users_data = [
        {
            "tenant_id": tenant_id,
            "external_id": "user123",
            "email": "john.doe@example.com",
            "phone": "+1234567890",
            "timezone": "America/New_York",
            "display_name": "John Doe",
            "metadata": {"department": "Engineering", "role": "Developer"}
        },
        {
            "tenant_id": tenant_id,
            "external_id": "user456",
            "email": "jane.smith@example.com",
            "phone": "+1234567891",
            "timezone": "Europe/London",
            "display_name": "Jane Smith",
            "metadata": {"department": "Marketing", "role": "Manager"}
        },
        {
            "tenant_id": tenant_id,
            "external_id": "user789",
            "email": "bob.wilson@example.com",
            "phone": None,  # No phone for this user
            "timezone": "Asia/Tokyo",
            "display_name": "Bob Wilson",
            "metadata": {"department": "Sales", "role": "Sales Rep"}
        }
    ]
    
    created_users = []
    for user_data in users_data:
        user = await user_repo.create(user_data)
        created_users.append(user)
        print(f"✅ Created user: {user.display_name} ({user.email})")
    
    return created_users


async def create_sample_templates(template_repo: TemplateRepository, tenant_id: str) -> list[Template]:
    """Create sample templates for testing."""
    templates_data = [
        {
            "tenant_id": tenant_id,
            "name": "Welcome Email",
            "slug": "welcome-email",
            "email_subject": "Welcome to NotiFlow, {{ name }}!",
            "email_body": """
                <h1>Welcome, {{ name }}!</h1>
                <p>Thank you for joining NotiFlow. We're excited to have you on board.</p>
                <p>Your account has been created with email: {{ email }}</p>
                {% if company %}
                <p>Company: {{ company }}</p>
                {% endif %}
                <p>Best regards,<br>The NotiFlow Team</p>
            """,
            "sms_body": "Welcome to NotiFlow, {{ name }}! Your account is ready.",
            "variables_schema": [
                {"name": "name", "type": "string", "required": True},
                {"name": "email", "type": "string", "required": True},
                {"name": "company", "type": "string", "required": False}
            ],
            "category": "transactional",
            "description": "Welcome email for new users",
            "is_active": True
        },
        {
            "tenant_id": tenant_id,
            "name": "Password Reset",
            "slug": "password-reset",
            "email_subject": "Reset your NotiFlow password",
            "email_body": """
                <h1>Password Reset Request</h1>
                <p>Hi {{ name }},</p>
                <p>We received a request to reset your password for your NotiFlow account.</p>
                <p>Click the link below to reset your password:</p>
                <p><a href="{{ reset_link }}" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Reset Password</a></p>
                <p>This link will expire in 1 hour.</p>
                <p>If you didn't request this password reset, please ignore this email.</p>
                <p>Best regards,<br>The NotiFlow Team</p>
            """,
            "sms_body": "NotiFlow: Reset your password at {{ reset_link }}",
            "variables_schema": [
                {"name": "name", "type": "string", "required": True},
                {"name": "reset_link", "type": "string", "required": True}
            ],
            "category": "transactional",
            "description": "Password reset notification",
            "is_active": True
        },
        {
            "tenant_id": tenant_id,
            "name": "System Alert",
            "slug": "system-alert",
            "email_subject": "🚨 System Alert: {{ alert_type }}",
            "email_body": """
                <div style="background: #fff3cd; border: 1px solid #ffeaa7; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                    <h3 style="color: #856404; margin-top: 0;">⚠️ Alert</h3>
                </div>
                <div style="background: #f8d7da; border-left: 4px solid #f5c6cb; padding: 20px;">
                    <p><strong>Alert Type:</strong> {{ alert_type }}</p>
                    <p><strong>Message:</strong> {{ message }}</p>
                    <p><strong>Time:</strong> {{ timestamp }}</p>
                    {% if service %}
                    <p><strong>Service:</strong> {{ service }}</p>
                    {% endif %}
                </div>
            """,
            "sms_body": "🚨 Alert: {{ alert_type }} - {{ message }}",
            "webhook_payload": """
                {
                    "alert_type": "{{ alert_type }}",
                    "message": "{{ message }}",
                    "timestamp": "{{ timestamp }}",
                    "service": "{{ service | default('unknown') }}",
                    "severity": "{{ severity | default('medium') }}"
                }
            """,
            "variables_schema": [
                {"name": "alert_type", "type": "string", "required": True},
                {"name": "message", "type": "string", "required": True},
                {"name": "timestamp", "type": "string", "required": True},
                {"name": "service", "type": "string", "required": False},
                {"name": "severity", "type": "string", "required": False}
            ],
            "category": "alert",
            "description": "System alert notifications",
            "is_active": True
        }
    ]
    
    created_templates = []
    for template_data in templates_data:
        template = await template_repo.create(template_data)
        created_templates.append(template)
        print(f"✅ Created template: {template.name} ({template.slug})")
    
    return created_templates


async def create_sample_webhook(webhook_repo: WebhookConfigRepository, tenant_id: str) -> WebhookConfig:
    """Create a sample webhook configuration."""
    webhook_data = {
        "tenant_id": tenant_id,
        "name": "Slack Notifications",
        "url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
        "secret": "your-webhook-secret-key",
        "headers": {
            "Content-Type": "application/json",
            "User-Agent": "NotiFlow-Webhook/1.0"
        },
        "max_retries": 3,
        "timeout_seconds": 10,
        "is_active": True
    }
    
    webhook = await webhook_repo.create(webhook_data)
    print(f"✅ Created webhook: {webhook.name}")
    print(f"   URL: {webhook.url}")
    
    return webhook


async def create_sample_preferences(user_repo: UserRepository, users: list[User]) -> None:
    """Create sample user preferences."""
    from app.repositories.preference_repo import UserPreferenceRepository
    from app.db.models.user_preference import UserChannelPreference
    
    pref_repo = UserPreferenceRepository(user_repo.db)
    
    for user in users:
        # John Doe - All channels enabled
        await pref_repo.upsert_preference(str(user.id), "email", True)
        await pref_repo.upsert_preference(str(user.id), "sms", True)
        await pref_repo.upsert_preference(str(user.id), "webhook", True)
        
        # Jane Smith - Email and SMS only
        if user.external_id == "user456":
            await pref_repo.upsert_preference(str(user.id), "email", True)
            await pref_repo.upsert_preference(str(user.id), "sms", True)
            await pref_repo.upsert_preference(str(user.id), "webhook", False)
        
        # Bob Wilson - Email only (no phone)
        if user.external_id == "user789":
            await pref_repo.upsert_preference(str(user.id), "email", True)
            await pref_repo.upsert_preference(str(user.id), "sms", False)
            await pref_repo.upsert_preference(str(user.id), "webhook", False)
        
        print(f"✅ Created preferences for {user.display_name}")


async def create_sample_quiet_hours(user_repo: UserRepository, users: list[User]) -> None:
    """Create sample quiet hours rules."""
    from app.repositories.preference_repo import QuietHoursRepository
    from app.db.models.quiet_hours import QuietHours
    
    quiet_repo = QuietHoursRepository(user_repo.db)
    
    for user in users:
        # John Doe - Weekday quiet hours (22:00-08:00)
        if user.external_id == "user123":
            for day in range(5):  # Monday-Friday
                await quiet_repo.upsert_rule(
                    str(user.id),
                    day,
                    time(22, 0),  # 10 PM
                    time(8, 0),   # 8 AM
                    user.timezone
                )
        
        # Jane Smith - Weekend quiet hours (23:00-09:00)
        if user.external_id == "user456":
            for day in [5, 6]:  # Saturday-Sunday
                await quiet_repo.upsert_rule(
                    str(user.id),
                    day,
                    time(23, 0),  # 11 PM
                    time(9, 0),   # 9 AM
                    user.timezone
                )
        
        print(f"✅ Created quiet hours for {user.display_name}")


async def main():
    """Main seeding function."""
    print("🌱 Seeding NotiFlow database with sample data...")
    
    async with get_async_session() as db:
        try:
            # Initialize repositories
            tenant_repo = TenantRepository(db)
            user_repo = UserRepository(db)
            template_repo = TemplateRepository(db)
            webhook_repo = WebhookConfigRepository(db)
            
            # Create sample data
            tenant = await create_sample_tenant(tenant_repo)
            users = await create_sample_users(user_repo, str(tenant.id))
            templates = await create_sample_templates(template_repo, str(tenant.id))
            webhook = await create_sample_webhook(webhook_repo, str(tenant.id))
            await create_sample_preferences(user_repo, users)
            await create_sample_quiet_hours(user_repo, users)
            
            print("\n🎉 Sample data created successfully!")
            print(f"\n📊 Summary:")
            print(f"   Tenants: 1")
            print(f"   Users: {len(users)}")
            print(f"   Templates: {len(templates)}")
            print(f"   Webhooks: 1")
            print(f"   Preferences: {len(users)}")
            print(f"   Quiet Hours: {len(users)}")
            print(f"\n🔑 API Key for testing:")
            print(f"   {generate_api_key()['full']}")
            
            # Commit the transaction
            await db.commit()
            
        except Exception as e:
            print(f"❌ Error creating sample data: {e}")
            await db.rollback()
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
