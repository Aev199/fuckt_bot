from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.backend.api.dependencies import get_current_user, get_current_user_for_media
from app.backend.db import crud
from app.backend.db.database import get_session
from app.backend.db.models import User
from app.backend.schemas.common import MessageResponse
from app.backend.schemas.material import MaterialCreate, MaterialListResponse, MaterialUpdate
from app.backend.services.telegram_files import download_telegram_file


router = APIRouter(prefix="/api/materials", tags=["materials"])


@router.get("", response_model=MaterialListResponse)
async def get_materials(
    q: str | None = Query(default=None),
    category_id: int | None = Query(default=None),
    favorite: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MaterialListResponse:
    items, total = await crud.list_materials(
        session=session,
        user_id=user.id,
        q=q,
        category_id=category_id,
        favorite=favorite,
        limit=limit,
        offset=offset,
    )
    return MaterialListResponse(items=[crud.serialize_material(item) for item in items], total=total)


@router.post("")
async def post_material(
    payload: MaterialCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        material = await crud.create_material(session=session, user_id=user.id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return crud.serialize_material(material).model_dump(mode="json")


@router.get("/{material_id}")
async def get_material_by_id(
    material_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        material = await crud.get_material(session=session, user_id=user.id, material_id=material_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return crud.serialize_material(material).model_dump(mode="json")


@router.patch("/{material_id}")
async def patch_material(
    material_id: int,
    payload: MaterialUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        material = await crud.update_material(session=session, user_id=user.id, material_id=material_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return crud.serialize_material(material).model_dump(mode="json")


@router.delete("/{material_id}", response_model=MessageResponse)
async def delete_material(
    material_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    try:
        await crud.delete_material(session=session, user_id=user.id, material_id=material_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return MessageResponse(message="Material deleted")


@router.post("/{material_id}/favorite")
async def toggle_favorite(
    material_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        material = await crud.toggle_favorite(session=session, user_id=user.id, material_id=material_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return crud.serialize_material(material).model_dump(mode="json")


@router.get("/{material_id}/attachments/{attachment_id}/content")
async def get_attachment_content(
    material_id: int,
    attachment_id: int,
    user: User = Depends(get_current_user_for_media),
    session: AsyncSession = Depends(get_session),
) -> Response:
    try:
        attachment = await crud.get_material_attachment(
            session=session,
            user_id=user.id,
            material_id=material_id,
            attachment_id=attachment_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if not attachment.file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment file path is missing")

    try:
        content = await download_telegram_file(attachment.file_path)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to download attachment") from exc

    return Response(content=content, media_type=attachment.mime_type or "application/octet-stream")


@router.delete("/{material_id}/attachments/{attachment_id}", response_model=MessageResponse)
async def delete_attachment(
    material_id: int,
    attachment_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    try:
        await crud.delete_material_attachment(
            session=session,
            user_id=user.id,
            material_id=material_id,
            attachment_id=attachment_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return MessageResponse(message="Attachment deleted")
