import cloudinary
import cloudinary.uploader
from fastapi import UploadFile, HTTPException
from app.core.config import settings

# Konfigurasi Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)

async def upload_image(file: UploadFile, folder: str = "products") -> str:
    """Upload gambar ke Cloudinary dan return URL"""
    
    # Validasi tipe file
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/jpg"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )
    
    # Validasi ukuran file (maks 5MB)
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="File too large. Max 5MB"
        )
    
    try:
        upload_result = cloudinary.uploader.upload(
            file.file,
            folder=folder,
            transformation=[
                {"width": 800, "height": 800, "crop": "limit"},
                {"quality": "auto"},
                {"fetch_format": "auto"}
            ]
        )
        return upload_result['secure_url']
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )