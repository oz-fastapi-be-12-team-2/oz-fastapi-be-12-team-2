from typing import Optional

from pydantic import BaseModel, Field


# 업로드 옵션(선택): 변환/폴더 등
class UploadImageOptions(BaseModel):
    # Cloudinary 폴더 경로 (예: myapp/diary)
    folder: Optional[str] = Field(default=None, description="업로드 폴더")
    # 가로/세로 리사이즈(선택)
    width: Optional[int] = Field(default=None, ge=1, description="리사이즈 가로(px)")
    height: Optional[int] = Field(default=None, ge=1, description="리사이즈 세로(px)")
    # 자르기 모드(예: 'scale', 'fill', 'fit', 'limit' 등)
    crop: Optional[str] = Field(default=None, description="자르기 모드")
    # 품질(예: 'auto' 또는 1~100)
    quality: Optional[str] = Field(default=None, description="이미지 품질")


class UploadImageResponse(BaseModel):
    # Cloudinary 결과(필요한 핵심만 노출)
    public_id: str
    url: str
    secure_url: str
    width: int
    height: int
    format: str
    bytes: int
