import asyncio
import time
import cloudinary
import cloudinary.uploader
from fastapi import UploadFile, HTTPException
from app.core.config import settings

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)

async def upload_image(file: UploadFile, folder: str = "products") -> str:
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/jpg"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )

    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="File too large. Max 5MB"
        )
    
    try:
        def _upload():
            return cloudinary.uploader.upload(
                file.file,
                folder=folder,
                transformation=[
                    {"width": 800, "height": 800, "crop": "limit"},
                    {"quality": "auto"},
                    {"fetch_format": "auto"}
                ]
            )
        start = time.time()
        upload_result = await asyncio.wait_for(asyncio.to_thread(_upload), timeout=30.0)
        elapsed = time.time() - start
        print(f"Cloudinary upload took {elapsed:.2f} seconds")
        return upload_result['secure_url']
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=408,
            detail="Upload to Cloudinary timed out after 30 seconds"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )