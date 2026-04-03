from __future__ import annotations

import re

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.backend.db.models import Category, Material, MaterialAttachment, MaterialTag, Tag, User
from app.backend.schemas.category import CategoryCreate, CategoryTreeNode
from app.backend.schemas.material import MaterialAttachmentRead, MaterialCreate, MaterialRead, MaterialUpdate


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    normalized = value.strip().lower().replace("ё", "е")
    normalized = _SLUG_RE.sub("-", normalized)
    return normalized.strip("-") or "item"


async def get_or_create_user(session: AsyncSession, telegram_id: int, username: str | None) -> User:
    user = (
        await session.execute(select(User).where(User.telegram_id == telegram_id))
    ).scalar_one_or_none()

    if user is None:
        user = User(telegram_id=telegram_id, username=username)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    if user.username != username:
        user.username = username
        await session.commit()
        await session.refresh(user)

    return user


async def list_categories(session: AsyncSession, user_id: int) -> list[dict]:
    rows = (
        await session.execute(
            select(
                Category,
                func.count(Material.id).label("materials_count"),
            )
            .outerjoin(Material, Material.category_id == Category.id)
            .where(Category.user_id == user_id)
            .group_by(Category.id)
            .order_by(Category.parent_id.asc().nullsfirst(), Category.name.asc())
        )
    ).all()

    items: list[dict] = []
    for category, materials_count in rows:
        items.append(
            {
                "id": category.id,
                "name": category.name,
                "slug": category.slug,
                "parent_id": category.parent_id,
                "created_at": category.created_at,
                "materials_count": materials_count,
            }
        )
    return items


async def list_category_tree(session: AsyncSession, user_id: int) -> list[CategoryTreeNode]:
    flat_categories = await list_categories(session=session, user_id=user_id)
    root_nodes: list[CategoryTreeNode] = []
    children_map: dict[int, list[CategoryTreeNode]] = {}

    for item in flat_categories:
        node = CategoryTreeNode(
            id=item["id"],
            name=item["name"],
            slug=item["slug"],
            parent_id=item["parent_id"],
            materials_count=item["materials_count"],
            children=[],
        )
        if node.parent_id is None:
            root_nodes.append(node)
        else:
            children_map.setdefault(node.parent_id, []).append(node)

    for root in root_nodes:
        root.children = children_map.get(root.id, [])

    return root_nodes


async def create_category(session: AsyncSession, user_id: int, payload: CategoryCreate) -> Category:
    parent = None
    if payload.parent_id is not None:
        parent = await _get_user_category(session=session, user_id=user_id, category_id=payload.parent_id)
        if parent.parent_id is not None:
            raise ValueError("Only one level of subcategories is allowed")

    base_slug = slugify(payload.name)
    slug = await _next_category_slug(session, user_id=user_id, base_slug=base_slug)

    category = Category(
        user_id=user_id,
        name=payload.name.strip(),
        slug=slug,
        parent_id=parent.id if parent else None,
    )
    session.add(category)
    await session.commit()
    await session.refresh(category)
    return category


async def create_material(session: AsyncSession, user_id: int, payload: MaterialCreate) -> Material:
    if payload.category_id is not None:
        await _ensure_category_belongs_to_user(session, user_id=user_id, category_id=payload.category_id)

    material = Material(
        user_id=user_id,
        category_id=payload.category_id,
        title=payload.title.strip(),
        content=payload.content.strip(),
        source_url=payload.source_url.strip() if payload.source_url else None,
        source_name=payload.source_name.strip() if payload.source_name else None,
        notes=payload.notes.strip() if payload.notes else None,
    )
    session.add(material)
    await session.flush()

    await _sync_tags(session, material=material, user_id=user_id, tags=payload.tags)
    await session.commit()
    return await get_material(session, user_id=user_id, material_id=material.id)


async def list_materials(
    session: AsyncSession,
    user_id: int,
    q: str | None = None,
    category_id: int | None = None,
    top_category_id: int | None = None,
    favorite: bool | None = None,
    has_attachments: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Material], int]:
    statement = (
        select(Material)
        .execution_options(populate_existing=True)
        .options(*_material_load_options())
        .where(Material.user_id == user_id)
        .order_by(Material.updated_at.desc(), Material.created_at.desc())
    )
    count_statement = select(func.count(Material.id)).where(Material.user_id == user_id)

    if category_id is not None:
        statement = statement.where(Material.category_id == category_id)
        count_statement = count_statement.where(Material.category_id == category_id)
    elif top_category_id is not None:
        child_ids = (
            await session.execute(
                select(Category.id).where(Category.user_id == user_id, Category.parent_id == top_category_id)
            )
        ).scalars().all()
        branch_ids = [top_category_id, *child_ids]
        statement = statement.where(Material.category_id.in_(branch_ids))
        count_statement = count_statement.where(Material.category_id.in_(branch_ids))

    if favorite is not None:
        statement = statement.where(Material.is_favorite.is_(favorite))
        count_statement = count_statement.where(Material.is_favorite.is_(favorite))

    if has_attachments is not None:
        attachment_exists = select(MaterialAttachment.id).where(MaterialAttachment.material_id == Material.id)
        if has_attachments:
            statement = statement.where(attachment_exists.exists())
            count_statement = count_statement.where(attachment_exists.exists())
        else:
            statement = statement.where(~attachment_exists.exists())
            count_statement = count_statement.where(~attachment_exists.exists())

    if q:
        like_pattern = f"%{q.strip()}%"
        tag_match_ids = (
            await session.execute(
                select(MaterialTag.material_id)
                .join(Tag, Tag.id == MaterialTag.tag_id)
                .where(Tag.user_id == user_id, Tag.name.ilike(like_pattern))
            )
        ).scalars().all()
        conditions = or_(
            Material.title.ilike(like_pattern),
            Material.content.ilike(like_pattern),
            Material.notes.ilike(like_pattern),
            Material.source_name.ilike(like_pattern),
            Material.id.in_(tag_match_ids or [-1]),
        )
        statement = statement.where(conditions)
        count_statement = count_statement.where(conditions)

    total = (await session.execute(count_statement)).scalar_one()
    items = (
        await session.execute(statement.limit(limit).offset(offset))
    ).scalars().unique().all()
    return list(items), total


async def get_material(session: AsyncSession, user_id: int, material_id: int) -> Material:
    material = (
        await session.execute(
            select(Material)
            .execution_options(populate_existing=True)
            .options(*_material_load_options())
            .where(Material.id == material_id, Material.user_id == user_id)
        )
    ).scalar_one_or_none()
    if material is None:
        raise ValueError("Material not found")
    return material


async def update_material(session: AsyncSession, user_id: int, material_id: int, payload: MaterialUpdate) -> Material:
    material = await get_material(session, user_id=user_id, material_id=material_id)
    data = payload.model_dump(exclude_unset=True)

    if "category_id" in data and data["category_id"] is not None:
        await _ensure_category_belongs_to_user(session, user_id=user_id, category_id=data["category_id"])

    tags = data.pop("tags", None)
    for field_name, field_value in data.items():
        if isinstance(field_value, str):
            field_value = field_value.strip() or None
        setattr(material, field_name, field_value)

    if tags is not None:
        await _sync_tags(session, material=material, user_id=user_id, tags=tags)

    await session.commit()
    return await get_material(session, user_id=user_id, material_id=material.id)


async def delete_material(session: AsyncSession, user_id: int, material_id: int) -> None:
    material = await get_material(session, user_id=user_id, material_id=material_id)
    await session.delete(material)
    await session.commit()


async def toggle_favorite(session: AsyncSession, user_id: int, material_id: int) -> Material:
    material = await get_material(session, user_id=user_id, material_id=material_id)
    material.is_favorite = not material.is_favorite
    await session.commit()
    return await get_material(session, user_id=user_id, material_id=material.id)


async def add_material_attachment(
    session: AsyncSession,
    user_id: int,
    material_id: int,
    telegram_file_id: str | None,
    file_path: str | None,
    file_name: str | None = None,
    mime_type: str | None = None,
    caption: str | None = None,
) -> MaterialAttachment:
    material = await get_material(session=session, user_id=user_id, material_id=material_id)
    sort_order = (
        await session.execute(
            select(func.count(MaterialAttachment.id)).where(MaterialAttachment.material_id == material.id)
        )
    ).scalar_one()
    attachment = MaterialAttachment(
        material_id=material.id,
        telegram_file_id=telegram_file_id,
        file_path=file_path,
        file_name=file_name,
        mime_type=mime_type,
        caption=caption,
        sort_order=sort_order,
    )
    session.add(attachment)
    await session.commit()
    await session.refresh(attachment)
    return attachment


async def get_material_attachment(
    session: AsyncSession,
    user_id: int,
    material_id: int,
    attachment_id: int,
) -> MaterialAttachment:
    attachment = (
        await session.execute(
            select(MaterialAttachment)
            .join(Material, Material.id == MaterialAttachment.material_id)
            .where(
                MaterialAttachment.id == attachment_id,
                MaterialAttachment.material_id == material_id,
                Material.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if attachment is None:
        raise ValueError("Attachment not found")
    return attachment


async def delete_material_attachment(
    session: AsyncSession,
    user_id: int,
    material_id: int,
    attachment_id: int,
) -> None:
    attachment = await get_material_attachment(
        session=session,
        user_id=user_id,
        material_id=material_id,
        attachment_id=attachment_id,
    )
    await session.delete(attachment)
    await session.flush()

    remaining = (
        await session.execute(
            select(MaterialAttachment)
            .where(MaterialAttachment.material_id == material_id)
            .order_by(MaterialAttachment.sort_order.asc(), MaterialAttachment.id.asc())
        )
    ).scalars().all()
    for index, item in enumerate(remaining):
        item.sort_order = index

    await session.commit()


def serialize_material(material: Material) -> MaterialRead:
    category = material.category
    top_category_id = None
    top_category_name = None
    subcategory_id = None
    subcategory_name = None

    if category is not None:
        if category.parent is None:
            top_category_id = category.id
            top_category_name = category.name
        else:
            top_category_id = category.parent.id
            top_category_name = category.parent.name
            subcategory_id = category.id
            subcategory_name = category.name

    return MaterialRead(
        id=material.id,
        title=material.title,
        content=material.content,
        source_url=material.source_url,
        source_name=material.source_name,
        notes=material.notes,
        is_favorite=material.is_favorite,
        category_id=material.category_id,
        category_name=category.name if category else None,
        top_category_id=top_category_id,
        top_category_name=top_category_name,
        subcategory_id=subcategory_id,
        subcategory_name=subcategory_name,
        tags=[material_tag.tag.name for material_tag in material.material_tags],
        attachments=[
            MaterialAttachmentRead(
                id=attachment.id,
                telegram_file_id=attachment.telegram_file_id,
                file_name=attachment.file_name,
                mime_type=attachment.mime_type,
                caption=attachment.caption,
                sort_order=attachment.sort_order,
                created_at=attachment.created_at,
            )
            for attachment in material.attachments
        ],
        created_at=material.created_at,
        updated_at=material.updated_at,
    )


async def _next_category_slug(session: AsyncSession, user_id: int, base_slug: str) -> str:
    slug = base_slug
    index = 2
    while (
        await session.execute(select(Category.id).where(Category.user_id == user_id, Category.slug == slug))
    ).scalar_one_or_none() is not None:
        slug = f"{base_slug}-{index}"
        index += 1
    return slug


async def _get_user_category(session: AsyncSession, user_id: int, category_id: int) -> Category:
    category = (
        await session.execute(select(Category).where(Category.id == category_id, Category.user_id == user_id))
    ).scalar_one_or_none()
    if category is None:
        raise ValueError("Category not found")
    return category


async def _ensure_category_belongs_to_user(session: AsyncSession, user_id: int, category_id: int) -> None:
    await _get_user_category(session=session, user_id=user_id, category_id=category_id)


async def _sync_tags(session: AsyncSession, material: Material, user_id: int, tags: list[str]) -> None:
    normalized_tags = [tag.strip() for tag in tags if tag.strip()]

    existing_links = (
        await session.execute(select(MaterialTag).where(MaterialTag.material_id == material.id))
    ).scalars().all()
    for link in existing_links:
        await session.delete(link)
    await session.flush()

    for tag_name in normalized_tags:
        slug = slugify(tag_name)
        tag = (
            await session.execute(select(Tag).where(Tag.user_id == user_id, Tag.slug == slug))
        ).scalar_one_or_none()
        if tag is None:
            tag = Tag(user_id=user_id, name=tag_name, slug=slug)
            session.add(tag)
            await session.flush()

        session.add(MaterialTag(material_id=material.id, tag_id=tag.id))


def _material_load_options():
    return (
        selectinload(Material.category).selectinload(Category.parent),
        selectinload(Material.material_tags).selectinload(MaterialTag.tag),
        selectinload(Material.attachments),
    )
