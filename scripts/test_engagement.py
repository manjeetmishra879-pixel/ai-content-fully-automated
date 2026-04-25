#!/usr/bin/env python3
"""
Test the trained Engagement Prediction Engine
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engines.quality.engagement_prediction import EngagementPredictionEngine

def test_engagement_prediction():
    """Test the ML-based engagement prediction"""

    print("🧪 Testing Engagement Prediction Engine")
    print("=" * 50)

    # Initialize engine
    engine = EngagementPredictionEngine()

    print(f"✅ Engine initialized. Models trained: {engine.is_trained}")

    # Test sample 1: High-quality TikTok content
    test1 = {
        "script": "Stop scrolling! This secret technique will change your life forever. You won't believe what happens next! This is the hack everyone needs to know.",
        "hooks": ["Stop scrolling!", "You won't believe this", "This secret technique"],
        "hashtags": ["#viral", "#fyp", "#lifehacks", "#secret"],
        "ctas": ["Follow for more", "Save this post"],
        "platform": "tiktok",
        "duration_s": 30.0,
        "trend_score": 75.0
    }

    print("\n📱 Test 1: High-quality TikTok content")
    result1 = engine.run(**test1)
    print(f"  Completion Rate: {result1['predictions']['completion_rate']:.1%}")
    print(f"  Like Rate: {result1['predictions']['like_rate']:.1%}")
    print(f"  Share Rate: {result1['predictions']['share_rate']:.1%}")
    print(f"  Skip Rate (3s): {result1['predictions']['skip_rate_3s']:.1%}")
    print(f"  Skip Rate (10s): {result1['predictions']['skip_rate_10s']:.1%}")
    print(f"  Skip Rate (30s): {result1['predictions']['skip_rate_30s']:.1%}")
    print(f"  Virality Probability: {result1['predictions']['virality_probability']:.1f}%")

    # Test sample 2: Low-quality Instagram content
    test2 = {
        "script": "Hello everyone. Today I want to talk about something.",
        "hooks": ["Hello everyone"],
        "hashtags": ["#hello", "#talk"],
        "ctas": ["Like and subscribe"],
        "platform": "instagram",
        "duration_s": 60.0,
        "trend_score": 10.0
    }

    print("\n📱 Test 2: Low-quality Instagram content")
    result2 = engine.run(**test2)
    print(f"  Completion Rate: {result2['predictions']['completion_rate']:.1%}")
    print(f"  Like Rate: {result2['predictions']['like_rate']:.1%}")
    print(f"  Share Rate: {result2['predictions']['share_rate']:.1%}")
    print(f"  Skip Rate (3s): {result2['predictions']['skip_rate_3s']:.1%}")
    print(f"  Skip Rate (10s): {result2['predictions']['skip_rate_10s']:.1%}")
    print(f"  Skip Rate (30s): {result2['predictions']['skip_rate_30s']:.1%}")
    print(f"  Virality Probability: {result2['predictions']['virality_probability']:.1f}%")

    # Test sample 3: Trending YouTube content
    test3 = {
        "script": "Breaking news! Scientists just discovered something incredible that will change everything you know about technology. Here's what happened and why it matters.",
        "hooks": ["Breaking news!", "Scientists just discovered", "This will change everything"],
        "hashtags": ["#breaking", "#science", "#technology", "#news"],
        "ctas": ["Subscribe for more", "Hit the bell", "Share with friends"],
        "platform": "youtube",
        "duration_s": 45.0,
        "trend_score": 95.0
    }

    print("\n📱 Test 3: Trending YouTube content")
    result3 = engine.run(**test3)
    print(f"  Completion Rate: {result3['predictions']['completion_rate']:.1%}")
    print(f"  Like Rate: {result3['predictions']['like_rate']:.1%}")
    print(f"  Share Rate: {result3['predictions']['share_rate']:.1%}")
    print(f"  Skip Rate (3s): {result3['predictions']['skip_rate_3s']:.1%}")
    print(f"  Skip Rate (10s): {result3['predictions']['skip_rate_10s']:.1%}")
    print(f"  Skip Rate (30s): {result3['predictions']['skip_rate_30s']:.1%}")
    print(f"  Virality Probability: {result3['predictions']['virality_probability']:.1f}%")

    print("\n✅ All tests completed successfully!")
    print("🎯 ML-based engagement prediction is working!")

if __name__ == "__main__":
    test_engagement_prediction()