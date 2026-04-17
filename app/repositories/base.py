"""
Base repository class with common database operations.
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base repository with CRUD operations."""
    
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db
    
    async def get(self, id: Any) -> Optional[ModelType]:
        """Get a single record by ID."""
        stmt = select(self.model).where(self.model.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[Any] = None
    ) -> List[ModelType]:
        """Get multiple records with pagination and filtering."""
        stmt = select(self.model)
        
        # Apply filters
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    stmt = stmt.where(getattr(self.model, key) == value)
        
        # Apply ordering
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        
        # Apply pagination
        stmt = stmt.offset(skip).limit(limit)
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def create(self, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record."""
        if hasattr(obj_in, "dict"):
            obj_data = obj_in.dict()
        else:
            obj_data = obj_in
        
        db_obj = self.model(**obj_data)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj
    
    async def update(
        self,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """Update an existing record."""
        if hasattr(obj_in, "dict"):
            update_data = obj_in.dict(exclude_unset=True)
        else:
            update_data = obj_in
        
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj
    
    async def update_by_id(
        self,
        id: Any,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> Optional[ModelType]:
        """Update a record by ID."""
        db_obj = await self.get(id)
        if db_obj is None:
            return None
        return await self.update(db_obj, obj_in)
    
    async def delete(self, id: Any) -> Optional[ModelType]:
        """Delete a record by ID."""
        db_obj = await self.get(id)
        if db_obj is None:
            return None
        await self.db.delete(db_obj)
        await self.db.flush()
        return db_obj
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records with optional filters."""
        stmt = select(func.count(self.model.id))
        
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    stmt = stmt.where(getattr(self.model, key) == value)
        
        result = await self.db.execute(stmt)
        return result.scalar()
    
    async def exists(self, id: Any) -> bool:
        """Check if a record exists by ID."""
        stmt = select(func.count(self.model.id)).where(self.model.id == id)
        result = await self.db.execute(stmt)
        return result.scalar() > 0
    
    async def get_by_field(
        self,
        field_name: str,
        value: Any
    ) -> Optional[ModelType]:
        """Get a single record by field value."""
        if not hasattr(self.model, field_name):
            raise ValueError(f"Model {self.model.__name__} has no field {field_name}")
        
        stmt = select(self.model).where(getattr(self.model, field_name) == value)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_multi_by_field(
        self,
        field_name: str,
        value: Any,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """Get multiple records by field value."""
        if not hasattr(self.model, field_name):
            raise ValueError(f"Model {self.model.__name__} has no field {field_name}")
        
        stmt = (
            select(self.model)
            .where(getattr(self.model, field_name) == value)
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def search(
        self,
        query: str,
        fields: List[str],
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """Search records by text query across multiple fields."""
        conditions = []
        for field in fields:
            if hasattr(self.model, field):
                field_attr = getattr(self.model, field)
                conditions.append(field_attr.ilike(f"%{query}%"))
        
        if not conditions:
            return []
        
        stmt = (
            select(self.model)
            .where(or_(*conditions))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
