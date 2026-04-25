"""
Content generation tasks - AI-powered content creation.
"""

import logging
from datetime import datetime
from celery import shared_task
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import Post, User
import random
import time

logger = logging.getLogger(__name__)


# ============================================================================
# Content Generation Task
# ============================================================================

@shared_task(bind=True, name='app.tasks.content_tasks.generate_content')
def generate_content(self, user_id: int, topic: str, content_type: str, 
                    platforms: list, tone: str = "professional", 
                    language: str = "english"):
    """
    Generate AI-powered content for user.
    
    Args:
        user_id: User ID
        topic: Content topic/keyword
        content_type: Type of content (reel, short, carousel, etc.)
        platforms: List of target platforms
        tone: Tone of content (professional, casual, funny, inspirational)
        language: Content language
    
    Returns:
        dict: Generated content with scripts, hooks, hashtags, captions
    """
    db = SessionLocal()
    
    try:
        self.update_state(state='PROCESSING', meta={'progress': 10})
        
        # Verify user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        logger.info(f"Generating content for user {user_id}: {topic}")
        
        self.update_state(state='PROCESSING', meta={'progress': 30, 'stage': 'generating_content'})
        
        # Simulate AI content generation (replace with real AI service)
        time.sleep(2)  # Simulate processing time
        
        # Mock AI generation
        generated_data = {
            "script": f"Engaging content about {topic}. "
                     f"This is a {content_type} optimized for {', '.join(platforms)}. "
                     f"Tone: {tone}.",
            "title": f"{topic} - {content_type.title()}",
            "hooks": [
                f"Did you know about {topic}?",
                f"{topic} is trending right now",
                f"Explore the world of {topic}",
            ],
            "hashtags": [
                f"#{topic.replace(' ', '')}",
                "#trending",
                "#content",
                "#viral",
            ],
            "ctas": [
                "Follow for more",
                "Share this",
                "Comment below",
            ],
            "captions": {
                platform: f"{topic} content for {platform}" 
                for platform in platforms
            },
            "quality_score": random.uniform(75, 95),
            "virality_potential": random.uniform(60, 90),
        }
        
        self.update_state(state='PROCESSING', meta={'progress': 70, 'stage': 'saving_to_db'})
        
        # Save to database
        post = Post(
            user_id=user_id,
            title=generated_data["title"],
            script=generated_data["script"],
            category=tone,
            content_type=content_type,
            status="draft",
            hooks=generated_data["hooks"],
            captions=generated_data["captions"],
            quality_score=generated_data["quality_score"],
            virality_prediction=generated_data["virality_potential"],
            metadata={
                "generated_with_ai": True,
                "tone": tone,
                "language": language,
                "target_platforms": platforms,
                "generated_at": datetime.utcnow().isoformat(),
            }
        )
        
        db.add(post)
        db.commit()
        db.refresh(post)
        
        self.update_state(state='SUCCESS', meta={
            'progress': 100,
            'post_id': post.id,
            'stage': 'complete'
        })
        
        logger.info(f"Content generated successfully for user {user_id}, post ID: {post.id}")
        
        return {
            "post_id": post.id,
            "title": generated_data["title"],
            "script": generated_data["script"],
            "hooks": generated_data["hooks"],
            "hashtags": generated_data["hashtags"],
            "quality_score": generated_data["quality_score"],
            "virality_potential": generated_data["virality_potential"],
            "generated_at": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Content generation failed for user {user_id}: {str(e)}", exc_info=True)
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise
        
    finally:
        db.close()


# ============================================================================
# Batch Content Generation
# ============================================================================

@shared_task(bind=True, name='app.tasks.content_tasks.generate_batch_content')
def generate_batch_content(self, user_id: int, topics: list, content_type: str, 
                          platforms: list, tone: str = "professional"):
    """
    Generate multiple content pieces in batch.
    
    Args:
        user_id: User ID
        topics: List of topics for content
        content_type: Type of content
        platforms: Target platforms
        tone: Content tone
    
    Returns:
        dict: Results for all generated content
    """
    db = SessionLocal()
    results = []
    
    try:
        total_topics = len(topics)
        
        for idx, topic in enumerate(topics):
            progress = int((idx / total_topics) * 100)
            self.update_state(state='PROCESSING', meta={
                'progress': progress,
                'current_topic': topic,
                'completed': idx,
                'total': total_topics
            })
            
            # Call generate_content for each topic
            result = generate_content.apply_async(
                args=[user_id, topic, content_type, platforms, tone]
            )
            
            results.append({
                "topic": topic,
                "task_id": result.id,
                "status": result.status
            })
        
        logger.info(f"Batch content generation completed for user {user_id}")
        
        return {
            "batch_id": self.request.id,
            "user_id": user_id,
            "total_topics": total_topics,
            "results": results,
            "generated_at": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Batch content generation failed: {str(e)}", exc_info=True)
        raise
        
    finally:
        db.close()


# ============================================================================
# Content Optimization Task
# ============================================================================

@shared_task(bind=True, name='app.tasks.content_tasks.optimize_content')
def optimize_content(self, post_id: int, optimization_type: str = "seo"):
    """
    Optimize existing content for better performance.
    
    Optimization types:
    - seo: SEO optimization
    - engagement: Maximize engagement
    - viral: Maximize virality potential
    - accessibility: Improve accessibility
    
    Args:
        post_id: Post ID to optimize
        optimization_type: Type of optimization
    
    Returns:
        dict: Optimization results and recommendations
    """
    db = SessionLocal()
    
    try:
        self.update_state(state='PROCESSING', meta={'progress': 20, 'stage': 'analyzing'})
        
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise ValueError(f"Post {post_id} not found")
        
        logger.info(f"Optimizing post {post_id} for {optimization_type}")
        
        time.sleep(1)  # Simulate optimization processing
        
        self.update_state(state='PROCESSING', meta={'progress': 60, 'stage': 'generating_recommendations'})
        
        # Generate optimization recommendations
        recommendations = {
            "seo": [
                "Add target keywords to title",
                "Include primary keyword in first sentence",
                "Optimize hashtags for search",
            ],
            "engagement": [
                "Move hook earlier in script",
                "Add more questions to engage audience",
                "Include CTA within first 30 seconds",
            ],
            "viral": [
                "Increase hook intensity",
                "Add trending elements",
                "Optimize for platform algorithm",
            ],
            "accessibility": [
                "Add captions/subtitles",
                "Include alt text for images",
                "Use sufficient color contrast",
            ],
        }
        
        optimization_data = recommendations.get(optimization_type, recommendations["seo"])
        
        # Update post quality score
        post.quality_score = min(post.quality_score + random.uniform(5, 15), 100)
        db.commit()
        
        self.update_state(state='SUCCESS', meta={
            'progress': 100,
            'post_id': post_id,
            'optimization_type': optimization_type
        })
        
        logger.info(f"Post {post_id} optimization completed")
        
        return {
            "post_id": post_id,
            "optimization_type": optimization_type,
            "recommendations": optimization_data,
            "quality_score_improved_to": post.quality_score,
            "optimized_at": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Content optimization failed: {str(e)}", exc_info=True)
        raise
        
    finally:
        db.close()
