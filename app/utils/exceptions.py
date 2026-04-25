"""
Custom exceptions
"""

class ContentPlatformException(Exception):
    """Base exception for content platform"""
    pass

class ContentGenerationException(ContentPlatformException):
    """Exception during content generation"""
    pass

class PublishingException(ContentPlatformException):
    """Exception during content publishing"""
    pass

class EngineException(ContentPlatformException):
    """Exception in engine execution"""
    pass
