#!/usr/bin/env python3
"""
Standalone training script for Engagement Prediction Engine.

This script trains ML models without importing the full application.
"""

import json
import pickle
import random
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler

# Model storage
MODEL_DIR = Path("models")
MODEL_DIR.mkdir(exist_ok=True)

PLATFORM_ENCODER = {
    "instagram": 0, "tiktok": 1, "youtube_shorts": 2, "youtube": 3,
    "facebook": 4, "x": 5, "linkedin": 6, "telegram": 7
}


def extract_features(script, hooks, hashtags, ctas, platform, duration_s, trend_score, quality_data):
    """Extract numerical features for ML model"""

    # Text features
    script_length = len(script)
    word_count = len(script.split())
    sentence_count = len([s for s in script.split('.') if s.strip()])

    # Hook features
    hook_count = len(hooks)
    avg_hook_length = sum(len(h) for h in hooks) / max(hook_count, 1)
    hook_power_words = sum(1 for h in hooks for word in ['stop', 'secret', 'never', 'why', 'how', 'this']
                           if word.lower() in h.lower())

    # Hashtag features
    hashtag_count = len(hashtags)
    hashtag_diversity = len(set(h.lower() for h in hashtags)) / max(hashtag_count, 1)

    # CTA features
    cta_count = len(ctas)
    cta_strength = sum(1 for cta in ctas for word in ['follow', 'save', 'share', 'comment', 'tag']
                       if word.lower() in cta.lower())

    # Quality features
    quality_score = quality_data.get("score", 50)
    hook_strength = quality_data.get("components", {}).get("hook_strength", 50)
    engagement_signals = quality_data.get("components", {}).get("engagement_signals", 5)
    originality = quality_data.get("components", {}).get("originality", 5)

    # Platform and content features
    platform_encoded = PLATFORM_ENCODER.get(platform, 0)
    duration_factor = 1.0 - abs(duration_s - 30) / 60  # Optimal around 30s

    # Trend and timing features
    trend_factor = min(trend_score / 100, 1.0)

    return [
        script_length, word_count, sentence_count,
        hook_count, avg_hook_length, hook_power_words,
        hashtag_count, hashtag_diversity,
        cta_count, cta_strength,
        quality_score, hook_strength, engagement_signals, originality,
        platform_encoded, duration_s, duration_factor, trend_factor
    ]


def generate_training_data(num_samples=2000):
    """Generate synthetic training data"""

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


def train_models(training_data):
    """Train ML models"""

    # Prepare training data
    X = []
    y = {metric: [] for metric in ["completion_rate", "like_rate", "share_rate", "skip_3s", "skip_10s", "skip_30s", "virality"]}

    for sample in training_data:
        features = extract_features(
            script=sample.get("script", ""),
            hooks=sample.get("hooks", []),
            hashtags=sample.get("hashtags", []),
            ctas=sample.get("ctas", []),
            platform=sample.get("platform", "instagram"),
            duration_s=sample.get("duration_s", 30.0),
            trend_score=sample.get("trend_score", 0.0),
            quality_data=sample.get("quality_data", {})
        )
        X.append(features)

        # Extract target values
        for metric in y.keys():
            if metric in sample:
                y[metric].append(sample[metric])

    X = np.array(X)

    # Fit scaler
    scaler = StandardScaler()
    scaler.fit(X)

    # Train models
    results = {}
    model_files = {
        "completion_rate": "completion_rf.pkl",
        "like_rate": "like_rf.pkl",
        "share_rate": "share_rf.pkl",
        "skip_3s": "skip_3s_rf.pkl",
        "skip_10s": "skip_10s_rf.pkl",
        "skip_30s": "skip_30s_rf.pkl",
        "virality": "virality_gb.pkl"
    }

    for metric in y.keys():
        if len(y[metric]) >= 20:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y[metric], test_size=0.2, random_state=42
            )

            # Choose model type
            if metric == "virality":
                model = GradientBoostingRegressor(n_estimators=100, random_state=42)
            else:
                model = RandomForestRegressor(n_estimators=100, random_state=42)

            model.fit(X_train, y_train)

            # Evaluate
            y_pred = model.predict(X_test)
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)

            # Save model
            model_path = MODEL_DIR / model_files[metric]
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)

            results[metric] = {
                "mae": round(mae, 4),
                "r2_score": round(r2, 4),
                "samples": len(y_train) + len(y_test)
            }

    # Save scaler
    with open(MODEL_DIR / "feature_scaler.pkl", 'wb') as f:
        pickle.dump(scaler, f)

    return {
        "trained_metrics": list(results.keys()),
        "performance": results,
        "total_samples": len(X),
        "models_saved": len(results)
    }


def main():
    print("🎯 Training Engagement Prediction Models (Standalone)")
    print("=" * 60)

    # Generate training data
    print("📊 Generating training data...")
    training_data = generate_training_data(2000)
    print(f"✅ Generated {len(training_data)} training samples")

    # Save sample data for inspection
    sample_file = Path("models/training_sample.json")
    with open(sample_file, 'w') as f:
        json.dump(training_data[:5], f, indent=2)
    print(f"💾 Saved sample training data to {sample_file}")

    # Train models
    print("\n🤖 Training ML models...")
    results = train_models(training_data)

    print("✅ Training completed!")
    print(f"📈 Trained {results['models_saved']} models on {results['total_samples']} samples")

    print("\n📊 Model Performance:")
    for metric, perf in results['performance'].items():
        print(f"  {metric}: MAE={perf['mae']:.4f}, R²={perf['r2_score']:.4f} ({perf['samples']} samples)")

    print("\n✅ Models are now trained and ready for use!")
    print("💡 In production, replace synthetic data with real engagement metrics from your published content.")


if __name__ == "__main__":
    main()