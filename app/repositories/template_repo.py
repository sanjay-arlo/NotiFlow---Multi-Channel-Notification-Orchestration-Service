"""
Template repository with specialized queries.
"""

from typing import List, Optional

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.template import Template
from app.repositories.base import BaseRepository


class TemplateRepository(BaseRepository[Template, dict, dict]):
    """Repository for template operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Template, db)
    
    async def get_by_tenant_and_slug(
        self,
        tenant_id: str,
        slug: str
    ) -> Optional[Template]:
        """Get template by tenant and slug."""
        stmt = select(Template).where(
            and_(
                Template.tenant_id == tenant_id,
                Template.slug == slug,
                Template.is_active == True
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_multi_by_tenant(
        self,
        tenant_id: str,
        category: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Template]:
        """Get templates for a tenant."""
        conditions = [
            Template.tenant_id == tenant_id,
            Template.is_active == True
        ]
        
        if category:
            conditions.append(Template.category == category)
        
        stmt = (
            select(Template)
            .where(and_(*conditions))
            .order_by(Template.name.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def search_templates(
        self,
        query: str,
        tenant_id: Optional[str] = None,
        category: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Template]:
        """Search templates by name or description."""
        conditions = [
            or_(
                Template.name.ilike(f"%{query}%"),
                Template.description.ilike(f"%{query}%"),
                Template.slug.ilike(f"%{query}%")
            ),
            Template.is_active == True
        ]
        
        if tenant_id:
            conditions.append(Template.tenant_id == tenant_id)
        
        if category:
            conditions.append(Template.category == category)
        
        stmt = (
            select(Template)
            .where(and_(*conditions))
            .order_by(Template.name.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_by_category(
        self,
        category: str,
        tenant_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Template]:
        """Get templates by category."""
        conditions = [
            Template.category == category,
            Template.is_active == True
        ]
        
        if tenant_id:
            conditions.append(Template.tenant_id == tenant_id)
        
        stmt = (
            select(Template)
            .where(and_(*conditions))
            .order_by(Template.name.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_templates_with_channel(
        self,
        channel: str,
        tenant_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Template]:
        """Get templates that support a specific channel."""
        channel_field_map = {
            "email": Template.email_body.is_not(None),
            "sms": Template.sms_body.is_not(None),
            "webhook": Template.webhook_payload.is_not(None)
        }
        
        conditions = [
            channel_field_map.get(channel, Template.email_body.is_not(None)),
            Template.is_active == True
        ]
        
        if tenant_id:
            conditions.append(Template.tenant_id == tenant_id)
        
        stmt = (
            select(Template)
            .where(and_(*conditions))
            .order_by(Template.name.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def count_by_tenant(
        self,
        tenant_id: str,
        category: Optional[str] = None
    ) -> int:
        """Count templates for a tenant."""
        conditions = [
            Template.tenant_id == tenant_id,
            Template.is_active == True
        ]
        
        if category:
            conditions.append(Template.category == category)
        
        stmt = select(Template).where(and_(*conditions))
        result = await self.db.execute(stmt)
        return len(result.scalars().all())
    
    async def count_by_category(
        self,
        tenant_id: Optional[str] = None
    ) -> dict[str, int]:
        """Count templates grouped by category."""
        conditions = [Template.is_active == True]
        
        if tenant_id:
            conditions.append(Template.tenant_id == tenant_id)
        
        stmt = select(
            Template.category,
            Template.tenant_id,
            func.count(Template.id).label("count")
        ).where(and_(*conditions)).group_by(Template.category, Template.tenant_id)
        
        result = await self.db.execute(stmt)
        counts = {}
        for row in result:
            if row.tenant_id not in counts:
                counts[row.tenant_id] = {}
            counts[row.tenant_id][row.category] = row.count
        
        return counts
    
    async def deactivate_template(self, id: str) -> Optional[Template]:
        """Deactivate a template."""
        return await self.update_by_id(id, {"is_active": False})
    
    async def activate_template(self, id: str) -> Optional[Template]:
        """Activate a template."""
        return await self.update_by_id(id, {"is_active": True})
    
    async def duplicate_template(
        self,
        original_id: str,
        new_slug: str,
        new_name: str,
        tenant_id: str
    ) -> Optional[Template]:
        """Duplicate a template for a tenant."""
        original = await self.get(original_id)
        if not original:
            return None
        
        # Create new template based on original
        new_template_data = {
            "tenant_id": tenant_id,
            "name": new_name,
            "slug": new_slug,
            "email_subject": original.email_subject,
            "email_body": original.email_body,
            "sms_body": original.sms_body,
            "webhook_payload": original.webhook_payload,
            "variables_schema": original.variables_schema,
            "category": original.category,
            "description": f"Copy of: {original.description or ''}",
            "is_active": True
        }
        
        return await self.create(new_template_data)
