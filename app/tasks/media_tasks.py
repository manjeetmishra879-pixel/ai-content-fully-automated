"""
Media generation tasks - Image and video creation.
"""

import logging
from datetime import datetime
from celery import shared_task
import time
from io import BytesIO
import random

from app.core.database import SessionLocal
from app.models import Asset, Post
from app.core.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# Image Generation Task
# ============================================================================

@shared_task(bind=True, name='app.tasks.media_tasks.generate_image')
def generate_image(self, user_id: int, post_id: int, prompt: str, 
                   style: str = "modern", resolution: str = "1080x1080"):
    """
    Generate image using AI (DALL-E, Midjourney, Stable Diffusion, etc.)
    
    Args:
        user_id: User ID
        post_id: Associated post ID
        prompt: Image generation prompt
        style: Image style (modern, vintage, artistic, minimalist, etc.)
        resolution: Image resolution (1080x1080, 1920x1080, etc.)
    
    Returns:
        dict: Asset details and MinIO storage location
    """
    db = SessionLocal()
    
    try:
        self.update_state(state='PROCESSING', meta={'progress': 15, 'stage': 'initializing'})
        
        # Verify post exists
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise ValueError(f"Post {post_id} not found")
        
        logger.info(f"Generating image for post {post_id}")
        
        self.update_state(state='PROCESSING', meta={'progress': 35, 'stage': 'calling_ai_service'})
        
        # Simulate AI image generation (replace with actual API call)
        time.sleep(3)  # Simulate API call time
        
        # Mock image generation
        image_data = {
            "filename": f"post_{post_id}_image_{int(time.time())}.png",
            "size_bytes": random.randint(500000, 2000000),  # 0.5-2 MB
            "width": int(resolution.split('x')[0]),
            "height": int(resolution.split('x')[1]),
            "format": "png",
            "prompt": prompt,
            "style": style,
        }
        
        self.update_state(state='PROCESSING', meta={'progress': 55, 'stage': 'uploading_to_minio'})
        
        # Mock MinIO upload (replace with actual MinIO upload)
        minio_path = f"images/{user_id}/{image_data['filename']}"
        minio_url = f"https://minio.example.com/{minio_path}"
        
        time.sleep(1)  # Simulate MinIO upload
        
        # Create asset record
        asset = Asset(
            user_id=user_id,
            post_id=post_id,
            asset_type="IMAGE",
            source="ai_generated",
            file_name=image_data["filename"],
            file_path=minio_path,
            file_url=minio_url,
            file_size=image_data["size_bytes"],
            mime_type="image/png",
            metadata={
                "ai_model": "stable_diffusion",
                "prompt": prompt,
                "style": style,
                "resolution": resolution,
                "generation_time": 3,
            },
            processing_status="ready",
        )
        
        db.add(asset)
        db.commit()
        db.refresh(asset)
        
        # Update post with image reference
        if not post.asset_ids:
            post.asset_ids = []
        post.asset_ids.append(asset.id)
        db.commit()
        
        self.update_state(state='SUCCESS', meta={
            'progress': 100,
            'asset_id': asset.id,
            'stage': 'complete'
        })
        
        logger.info(f"Image generated successfully: {asset.id}")
        
        return {
            "asset_id": asset.id,
            "post_id": post_id,
            "file_url": minio_url,
            "file_size": image_data["size_bytes"],
            "width": image_data["width"],
            "height": image_data["height"],
            "prompt": prompt,
            "style": style,
            "generated_at": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Image generation failed: {str(e)}", exc_info=True)
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise
        
    finally:
        db.close()


# ============================================================================
# Video Generation Task
# ============================================================================

@shared_task(bind=True, name='app.tasks.media_tasks.generate_video')
def generate_video(self, user_id: int, post_id: int, script: str, 
                   video_type: str = "short_form", duration: int = 30,
                   music: bool = True, subtitles: bool = True):
    """
    Generate video from script using AI video generation service.
    
    Args:
        user_id: User ID
        post_id: Associated post ID
        script: Video script/narration
        video_type: Type of video (short_form, long_form, tutorial, etc.)
        duration: Video duration in seconds
        music: Include background music
        subtitles: Include subtitles/captions
    
    Returns:
        dict: Generated video asset details
    """
    db = SessionLocal()
    
    try:
        self.update_state(state='PROCESSING', meta={'progress': 10, 'stage': 'preparing'})
        
        # Verify post exists
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise ValueError(f"Post {post_id} not found")
        
        logger.info(f"Generating video for post {post_id}, duration: {duration}s")
        
        self.update_state(state='PROCESSING', meta={'progress': 25, 'stage': 'calling_video_service'})
        
        # Simulate video generation (replace with actual API)
        # Real implementations would use Synthesia, D-ID, Runway AI, etc.
        generation_time = duration / 10  # Simulate based on duration
        time.sleep(min(generation_time, 5))  # Cap at 5 seconds for demo
        
        # Mock video data
        video_data = {
            "filename": f"post_{post_id}_video_{int(time.time())}.mp4",
            "size_bytes": random.randint(5000000, 50000000),  # 5-50 MB
            "width": 1080,
            "height": 1920,
            "fps": 30,
            "bitrate": "5000k",
            "duration": duration,
            "format": "mp4",
        }
        
        self.update_state(state='PROCESSING', meta={'progress': 60, 'stage': 'adding_effects_and_music'})
        
        # Simulate effect/music processing
        time.sleep(1)
        
        self.update_state(state='PROCESSING', meta={'progress': 80, 'stage': 'uploading_to_minio'})
        
        # Mock MinIO upload
        minio_path = f"videos/{user_id}/{video_data['filename']}"
        minio_url = f"https://minio.example.com/{minio_path}"
        
        time.sleep(1)
        
        # Create asset record
        asset = Asset(
            user_id=user_id,
            post_id=post_id,
            asset_type="VIDEO",
            source="ai_generated",
            file_name=video_data["filename"],
            file_path=minio_path,
            file_url=minio_url,
            file_size=video_data["size_bytes"],
            mime_type="video/mp4",
            metadata={
                "ai_model": "synthesia",
                "video_type": video_type,
                "duration": duration,
                "fps": video_data["fps"],
                "bitrate": video_data["bitrate"],
                "has_music": music,
                "has_subtitles": subtitles,
                "script": script[:200],  # Store first 200 chars
            },
            processing_status="ready",
        )
        
        db.add(asset)
        db.commit()
        db.refresh(asset)
        
        # Update post with video reference
        if not post.asset_ids:
            post.asset_ids = []
        post.asset_ids.append(asset.id)
        db.commit()
        
        self.update_state(state='SUCCESS', meta={
            'progress': 100,
            'asset_id': asset.id,
            'stage': 'complete'
        })
        
        logger.info(f"Video generated successfully: {asset.id}")
        
        return {
            "asset_id": asset.id,
            "post_id": post_id,
            "file_url": minio_url,
            "file_size": video_data["size_bytes"],
            "duration": duration,
            "resolution": f"{video_data['width']}x{video_data['height']}",
            "fps": video_data["fps"],
            "has_music": music,
            "has_subtitles": subtitles,
            "generated_at": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Video generation failed: {str(e)}", exc_info=True)
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise
        
    finally:
        db.close()


# ============================================================================
# Video Editing Task
# ============================================================================

@shared_task(bind=True, name='app.tasks.media_tasks.edit_video')
def edit_video(self, asset_id: int, edits: dict):
    """
    Edit existing video asset.
    
    Edits can include:
    - Trimming
    - Speed adjustments
    - Custom filters
    - Transitions
    - Text overlays
    
    Args:
        asset_id: Asset ID to edit
        edits: Dictionary of edit operations
    
    Returns:
        dict: Edited video details
    """
    db = SessionLocal()
    
    try:
        self.update_state(state='PROCESSING', meta={'progress': 20, 'stage': 'loading_video'})
        
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            raise ValueError(f"Asset {asset_id} not found")
        
        logger.info(f"Editing video asset {asset_id}")
        
        self.update_state(state='PROCESSING', meta={'progress': 50, 'stage': 'applying_edits'})
        
        # Simulate video editing processing
        time.sleep(2)
        
        self.update_state(state='PROCESSING', meta={'progress': 75, 'stage': 'uploading_edited_video'})
        
        # Create new asset record for edited version
        edited_filename = f"edited_{asset.file_name}"
        minio_path = f"videos/{asset.user_id}/{edited_filename}"
        minio_url = f"https://minio.example.com/{minio_path}"
        
        edited_asset = Asset(
            user_id=asset.user_id,
            post_id=asset.post_id,
            asset_type=asset.asset_type,
            source="ai_edited",
            file_name=edited_filename,
            file_path=minio_path,
            file_url=minio_url,
            file_size=asset.file_size,
            mime_type=asset.mime_type,
            metadata={
                **asset.metadata,
                "edited_from": asset_id,
                "edits_applied": edits,
            },
            processing_status="ready",
        )
        
        db.add(edited_asset)
        db.commit()
        db.refresh(edited_asset)
        
        self.update_state(state='SUCCESS', meta={
            'progress': 100,
            'asset_id': edited_asset.id,
        })
        
        logger.info(f"Video edited successfully: {edited_asset.id}")
        
        return {
            "original_asset_id": asset_id,
            "edited_asset_id": edited_asset.id,
            "file_url": minio_url,
            "edits_applied": edits,
            "edited_at": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Video editing failed: {str(e)}", exc_info=True)
        raise
        
    finally:
        db.close()
