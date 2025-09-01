from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.files.schema import UploadImageOptions, UploadImageResponse
from app.files.service import CloudinaryService

router = APIRouter(prefix="/files", tags=["Files"])


# -------------------------------
# 이미지 업로드 (Cloudinary)
# -------------------------------
@router.post(
    "/images",
    response_model=UploadImageResponse,
    summary="이미지 업로드(Cloudinary)",
)
async def upload_image(
    file: UploadFile = File(..., description="업로드할 이미지"),
    folder: str | None = Query(
        None, description="Cloudinary 폴더(미지정 시 기본값 사용)"
    ),
    width: int | None = Query(None, ge=1, description="리사이즈 가로"),
    height: int | None = Query(None, ge=1, description="리사이즈 세로"),
    crop: str | None = Query(None, description="자르기 모드(scale/fill/fit/limit 등)"),
    quality: str | None = Query(None, description="품질(auto 또는 1~100)"),
):
    """
    - 이미지 업로드 후 Cloudinary URL 반환
    - 필요 시 폴더/리사이즈/자르기/품질 옵션 지정 가능(모두 선택)
    """
    opts = UploadImageOptions(
        folder=folder,
        width=width,
        height=height,
        crop=crop,
        quality=quality,
    )
    return await CloudinaryService.upload_image(file, opts=opts)


# -------------------------------
# 이미지 삭제 (옵션)
# -------------------------------
@router.delete(
    "/images/{public_id}",
    summary="Cloudinary 이미지 삭제(옵션)",
)
async def delete_image(public_id: str):
    ok = await CloudinaryService.delete_image(public_id)
    if not ok:
        # 이미 삭제되었거나 없음
        raise HTTPException(status_code=404, detail="이미 존재하지 않는 이미지")
    return {"deleted": True}
