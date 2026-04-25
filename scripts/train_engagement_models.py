#!/usr/bin/env python3
"""
Training script for Engagement Prediction Engine.

This script demonstrates how to train ML models for engagement prediction
using historical data. In production, you would collect real engagement
data from published content.

Usage:
    python scripts/train_engagement_models.py
"""

import json
import random
from pathlib import Path

from app.engines.quality.engagement_prediction import EngagementPredictionEngine


def generate_sample_training_data(num_samples: int = 1000) -> list[dict]:
    """Generate synthetic training data for demonstration"""

    platforms = ["instagram", "tiktok", "youtube_shorts", "youtube", "facebook", "x", "linkedin"]
    hooks = [
        "Stop scrolling!", "You won't believe this", "This secret changed my life",
        "Why this happens", "How to fix this", "The truth about", "What really happens"
    ]
    hashtags = ["#viral", "#fyp", "#trending", "#tips", "#lifehacks", "#motivation"]
    ctas = ["Follow for more", "Save this", "Share with friends", "Tag someone", "Comment below"]

    training_data = []

    for _ in range(num_samples):
        platform = random.choice(platforms)
        duration = random.uniform(15, 90)

        # Generate realistic engagement based on platform and quality
        quality_score = random.uniform(30, 95)
        hook_strength = random.uniform(20, 80)
        originality = random.uniform(3, 10)
        engagement_signals = random.uniform(2, 12)

        # Base rates by platform
        base_rates = {
            "instagram": (0.55, 0.05, 0.012),
            "tiktok": (0.70, 0.08, 0.020),
            "youtube_shorts": (0.65, 0.04, 0.010),
            "youtube": (0.40, 0.03, 0.008),
            "facebook": (0.35, 0.03, 0.010),
            "x": (0.45, 0.02, 0.015),
            "linkedin": (0.50, 0.025, 0.012),
        }

        base_completion, base_like, base_share = base_rates[platform]

        # Apply quality modifiers
        completion = base_completion * (0.7 + quality_score/100 * 0.6) * (0.8 + hook_strength/100 * 0.4)
        completion = max(0.05, min(0.95, completion))

        like_rate = base_like * (0.5 + quality_score/100 * 0.8)
        like_rate = max(0.005, min(0.25, like_rate))

        share_rate = base_share * (0.5 + originality/10 * 0.6 + engagement_signals/15 * 0.4)
        share_rate = max(0.001, min(0.10, share_rate))

        # Skip rates (inverse relationship with completion)
        skip_3s = max(0.05, 0.3 - completion * 0.4)
        skip_10s = max(0.1, 0.5 - completion * 0.5)
        skip_30s = max(0.2, 0.7 - completion * 0.6)

        # Virality score
        virality = 100 * (0.4 * completion + 0.4 * like_rate * 5 + 0.2 * share_rate * 20)
        virality = min(99.0, virality)

        sample = {
            "script": f"This is a sample script about {random.choice(['technology', 'lifestyle', 'business', 'health'])} with some content.",
            "hooks": random.sample(hooks, random.randint(1, 3)),
            "hashtags": random.sample(hashtags, random.randint(2, 5)),
            "ctas": random.sample(ctas, random.randint(1, 2)),
            "platform": platform,
            "duration_s": duration,
            "trend_score": random.uniform(0, 100),
            "quality_data": {
                "score": quality_score,
                "components": {
                    "hook_strength": hook_strength,
                    "engagement_signals": engagement_signals,
                    "originality": originality
                }
            },
            # Target values for training
            "completion_rate": completion,
            "like_rate": like_rate,
            "share_rate": share_rate,
            "skip_3s": skip_3s,
            "skip_10s": skip_10s,
            "skip_30s": skip_30s,
            "virality": virality
        }

        training_data.append(sample)

    return training_data


def main():
    """Train the engagement prediction models"""

    print("🎯 Training Engagement Prediction Models")
    print("=" * 50)

    # Initialize engine
    engine = EngagementPredictionEngine()

    # Generate training data
    print("📊 Generating training data...")
    training_data = generate_sample_training_data(2000)
    print(f"✅ Generated {len(training_data)} training samples")

    # Save sample data for inspection
    sample_file = Path("models/training_sample.json")
    sample_file.parent.mkdir(exist_ok=True)

    with open(sample_file, 'w') as f:
        json.dump(training_data[:5], f, indent=2)  # Save first 5 samples
    print(f"💾 Saved sample training data to {sample_file}")

    # Train models
    print("\n🤖 Training ML models...")
    results = engine.train_models(training_data)

    if "error" in results:
        print(f"❌ Training failed: {results['error']}")
        return

    print("✅ Training completed!")
    print(f"📈 Trained {results['models_saved']} models on {results['total_samples']} samples")

    print("\n📊 Model Performance:")
    for metric, perf in results['performance'].items():
        print(f"  {metric}: MAE={perf['mae']:.4f}, R²={perf['r2_score']:.4f} ({perf['samples']} samples)")

    # Test the trained models
    print("\n🧪 Testing trained models...")
    test_sample = {
        "script": "Stop scrolling! This secret technique will change your life forever. You won't believe what happens next!",
        "hooks": ["Stop scrolling!", "You won't believe this"],
        "hashtags": ["#viral", "#lifehacks", "#secret"],
        "ctas": ["Follow for more", "Save this post"],
        "platform": "tiktok",
        "duration_s": 30.0,
        "trend_score": 75.0
    }

    prediction = engine.run(**test_sample)
    print("\n🎯 Sample Prediction:")
    print(f"  Platform: {prediction['platform']}")
    print(f"  Completion Rate: {prediction['predictions']['completion_rate']:.1%}")
    print(f"  Like Rate: {prediction['predictions']['like_rate']:.1%}")
    print(f"  Share Rate: {prediction['predictions']['share_rate']:.1%}")
    print(f"  Skip Rate (3s): {prediction['predictions']['skip_rate_3s']:.1%}")
    print(f"  Virality Probability: {prediction['predictions']['virality_probability']:.1f}%")

    print("\n✅ Models are now trained and ready for use!")
    print("💡 In production, replace synthetic data with real engagement metrics from your published content.")


if __name__ == "__main__":
    main()