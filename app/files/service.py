import os
import uuid
from functools import partial
from typing import Any, Dict, List, Optional, Sequence, Union

import anyio
import cloudinary  # type: ignore[import-untyped]
import cloudinary.uploader as cu  # type: ignore[import-untyped]
from fastapi import HTTPException, UploadFile

from app.files.schema import UploadImageOptions, UploadImageResponse

# ------------------------------------------------------------
# Cloudinary 기본 설정 (앱 시작 시 1회 설정)
# ------------------------------------------------------------
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)

# 허용 확장자/타입
ALLOWED_TYPES: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}

# 사이즈/개수 제한
MAX_SIZE_MB: float = float(os.getenv("CLOUDINARY_MAX_SIZE_MB", "5"))
MAX_BYTES: int = int(MAX_SIZE_MB * 1024 * 1024)
MAX_IMAGE_FILES: int = int(os.getenv("CLOUDINARY_MAX_FILES", "10"))


def _build_transformations(opts: UploadImageOptions | None) -> Dict[str, Any]:
    """
    Cloudinary에 전달할 변환/옵션 파라미터 구성.
    - 지정된 값만 포함(불필요 파라미터 제외)
    """
    params: Dict[str, Any] = {}
    if not opts:
        # 기본값 추천: 자동 포맷/퀄리티
        params["fetch_format"] = "auto"
        params["quality"] = "auto"
        return params

    if opts.folder:
        params["folder"] = opts.folder
    if opts.width:
        params["width"] = opts.width
    if opts.height:
        params["height"] = opts.height
    if opts.crop:
        params["crop"] = opts.crop
    if opts.quality:
        params["quality"] = opts.quality

    # 기본값(없으면 설정)
    params.setdefault("fetch_format", "auto")
    params.setdefault("quality", "auto")
    return params


def _unique_preserve_order(values: Sequence[str]) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for v in values:
        s = (v or "").strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


class CloudinaryService:
    # ============== 업로드 ==============
    @staticmethod
    async def upload_image(
        file: UploadFile,
        opts: Optional[UploadImageOptions] = None,
    ) -> UploadImageResponse:
        # 1) MIME 검증
        if file.content_type not in ALLOWED_TYPES:
            raise HTTPException(
                status_code=415, detail="이미지 형식만 허용합니다 (jpg/png/webp/gif)"
            )

        # 2) 크기 제한
        data = await file.read()
        if len(data) > MAX_BYTES:
            raise HTTPException(
                status_code=413, detail=f"파일이 너무 큽니다(최대 {int(MAX_SIZE_MB)}MB)"
            )

        # 3) 업로드 파라미터 준비
        params = _build_transformations(opts)
        params["public_id"] = uuid.uuid4().hex  # 명시적 public_id

        # 4) 동기 SDK → 스레드 오프로딩 (kwargs는 partial로 래핑)
        upload_call = partial(
            cu.upload,
            data,
            resource_type="image",
            **params,
        )

        try:
            res: dict[str, Any] = await anyio.to_thread.run_sync(upload_call)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"업로드 실패: {e}")

        # 5) 결과 매핑
        try:
            return UploadImageResponse(
                public_id=str(res["public_id"]),
                url=str(res["url"]),
                secure_url=str(res["secure_url"]),
                width=int(res["width"]),
                height=int(res["height"]),
                format=str(res["format"]),
                bytes=int(res["bytes"]),
            )
        except KeyError as ke:
            raise HTTPException(
                status_code=502, detail=f"업로드 응답 파싱 오류: 누락된 키 {ke!s}"
            )

    @staticmethod
    async def upload_images(
        files: Sequence[UploadFile] | None,
        opts: Optional[UploadImageOptions] = None,
    ) -> List[UploadImageResponse]:
        """
        파일 0~N개 동시 업로드.
        - 순서를 보존
        - 실패는 건너뛰고 성공만 반환
        """
        if not files:
            return []
        if len(files) > MAX_IMAGE_FILES:
            raise HTTPException(
                status_code=400,
                detail=f"이미지 최대 {MAX_IMAGE_FILES}개까지 업로드 가능합니다.",
            )

        import asyncio

        results: List[Union[UploadImageResponse, BaseException]] = await asyncio.gather(
            *(CloudinaryService.upload_image(f, opts) for f in files),
            return_exceptions=True,
        )

        out: List[UploadImageResponse] = []
        for r in results:
            if isinstance(r, BaseException):
                # TODO: 로깅/알림 등
                continue
            out.append(r)
        return out

    @staticmethod
    async def upload_images_to_urls(
        files: Sequence[UploadFile] | None,
        opts: Optional[UploadImageOptions] = None,
    ) -> List[str]:
        """
        파일 0~N개 업로드 → secure_url 리스트 반환(순서 보존, 중복 제거)
        """
        responses = await CloudinaryService.upload_images(files, opts)
        urls = [r.secure_url for r in responses]
        return _unique_preserve_order(urls)

    # ============== 삭제 ==============
    @staticmethod
    async def delete_image(public_id: str, invalidate: bool = True) -> bool:
        """
        업로드된 이미지를 Cloudinary에서 삭제
        - invalidate=True: CDN 무효화
        """
        destroy_call = partial(
            cu.destroy,
            public_id,
            invalidate=invalidate,
            resource_type="image",
        )
        try:
            res: dict[str, Any] = await anyio.to_thread.run_sync(destroy_call)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"삭제 실패: {e}")

        # res 예: {"result": "ok"} / {"result": "not found"}
        return res.get("result") == "ok"

    @staticmethod
    async def delete_images(
        public_ids: Sequence[str], invalidate: bool = True
    ) -> dict[str, bool]:
        """
        다중 삭제: 각 public_id별 성공 여부를 반환
        """
        if not public_ids:
            return {}
        import asyncio

        results = await asyncio.gather(
            *(
                CloudinaryService.delete_image(pid, invalidate=invalidate)
                for pid in public_ids
            ),
            return_exceptions=True,
        )
        out: dict[str, bool] = {}
        for pid, r in zip(public_ids, results):
            out[pid] = False if isinstance(r, BaseException) else bool(r)
        return out
