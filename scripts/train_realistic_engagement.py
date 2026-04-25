#!/usr/bin/env python3
"""
Realistic Training Script for Engagement Prediction Engine.

This script generates realistic training data that simulates real-world
engagement patterns and trains models with appropriate parameters.
"""

import json
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

LANGUAGE_ENCODER = {
    "english": 0, "hindi": 1, "spanish": 2, "french": 3,
    "german": 4, "arabic": 5, "portuguese": 6, "other": 7
}

FEATURE_NAMES = [
    "script_length", "word_count", "sentence_count",
    "hook_count", "avg_hook_length", "hook_power_words",
    "hashtag_count", "hashtag_diversity",
    "cta_count", "cta_strength",
    "quality_score", "hook_strength", "engagement_signals", "originality",
    "platform_encoded", "duration_s", "duration_factor", "trend_score",
    "language_encoded", "hour_of_day", "day_of_week", "is_weekend",
    "competitor_avg_engagement", "account_followers_log",
    "has_trending_audio", "seasonal_trend_factor"
]


def extract_features(sample):
    """Extract features from training sample"""
    script = sample.get("script", "")
    hooks = sample.get("hooks", [])
    hashtags = sample.get("hashtags", [])
    ctas = sample.get("ctas", [])
    platform = sample.get("platform", "instagram")
    duration_s = sample.get("duration_s", 30.0)
    trend_score = sample.get("trend_score", 0.0)
    quality_data = sample.get("quality_data", {})
    language = sample.get("language", "english")
    posting_hour = sample.get("posting_hour")
    competitor_engagement = sample.get("competitor_engagement", 0.0)
    account_followers = sample.get("account_followers", 1000)
    has_trending_audio = sample.get("has_trending_audio", False)
    seasonal_trend = sample.get("seasonal_trend", 1.0)

    # Text features
    script_length = len(script)
    word_count = len(script.split())
    sentence_count = len([s for s in script.split('.') if s.strip()])

    # Hook features
    hook_count = len(hooks)
    avg_hook_length = sum(len(h) for h in hooks) / max(hook_count, 1)
    hook_power_words = sum(1 for h in hooks for word in ['stop', 'secret', 'never', 'why', 'how', 'this',
                                                        'breaking', 'shocking', 'unbelievable', 'truth']
                           if word.lower() in h.lower())

    # Hashtag features
    hashtag_count = len(hashtags)
    hashtag_diversity = len(set(h.lower() for h in hashtags)) / max(hashtag_count, 1)

    # CTA features
    cta_count = len(ctas)
    cta_strength = sum(1 for cta in ctas for word in ['follow', 'save', 'share', 'comment', 'tag',
                                                     'subscribe', 'like', 'bell']
                       if word.lower() in cta.lower())

    # Quality features
    quality_score = quality_data.get("score", 50)
    hook_strength = quality_data.get("components", {}).get("hook_strength", 50)
    engagement_signals = quality_data.get("components", {}).get("engagement_signals", 5)
    originality = quality_data.get("components", {}).get("originality", 5)

    # Platform and content features
    platform_encoded = PLATFORM_ENCODER.get(platform, 0)
    duration_factor = 1.0 - abs(duration_s - 30) / 60

    # Language features
    language_encoded = LANGUAGE_ENCODER.get(language.lower(), 7)

    # Temporal features
    current_hour = posting_hour if posting_hour is not None else random.randint(0, 23)
    current_day = random.randint(0, 6)
    is_weekend = 1.0 if current_day >= 5 else 0.0

    # Social features
    competitor_avg_engagement = competitor_engagement
    account_followers_log = np.log10(max(account_followers, 1))
    has_trending_audio_encoded = 1.0 if has_trending_audio else 0.0
    seasonal_trend_factor = seasonal_trend

    return [
        script_length, word_count, sentence_count,
        hook_count, avg_hook_length, hook_power_words,
        hashtag_count, hashtag_diversity,
        cta_count, cta_strength,
        quality_score, hook_strength, engagement_signals, originality,
        platform_encoded, duration_s, duration_factor, trend_score,
        language_encoded, current_hour, current_day, is_weekend,
        competitor_avg_engagement, account_followers_log,
        has_trending_audio_encoded, seasonal_trend_factor
    ]


def generate_realistic_training_data(num_samples=1000):
    """Generate realistic training data that simulates real engagement patterns"""

    platforms = ["instagram", "tiktok", "youtube_shorts", "youtube", "facebook", "x", "linkedin"]
    languages = ["english", "hindi", "spanish", "french", "german", "arabic", "portuguese"]
    hooks = [
        "Stop scrolling!", "You won't believe this", "This secret changed my life",
        "Why this happens", "How to fix this", "The truth about", "What really happens",
        "Breaking news!", "This shocked me", "Never do this again"
    ]
    hashtags = ["#viral", "#fyp", "#trending", "#tips", "#lifehacks", "#motivation", "#funny", "#love"]
    ctas = ["Follow for more", "Save this", "Share with friends", "Tag someone", "Comment below", "Subscribe", "Like and share"]

    training_data = []

    for _ in range(num_samples):
        platform = random.choice(platforms)
        language = random.choice(languages)
        duration = random.uniform(15, 120)

        # Generate quality scores with realistic distributions
        quality_score = random.gauss(60, 20)  # Normal distribution around 60
        quality_score = max(0, min(100, quality_score))

        hook_strength = random.gauss(60, 25)
        hook_strength = max(0, min(100, hook_strength))

        engagement_signals = random.gauss(7, 3)
        engagement_signals = max(0, min(15, engagement_signals))

        originality = random.gauss(6, 2)
        originality = max(0, min(10, originality))

        # Generate content features
        num_hooks = random.randint(0, 4)
        num_hashtags = random.randint(0, 8)
        num_ctas = random.randint(0, 3)

        trend_score = random.uniform(0, 100)
        posting_hour = random.randint(0, 23)
        competitor_engagement = random.uniform(0, 50)
        account_followers = random.randint(100, 1000000)
        has_trending_audio = random.random() < 0.3  # 30% chance
        seasonal_trend = random.uniform(0.8, 1.5)

        # Base rates by platform (realistic industry averages)
        base_rates = {
            "instagram": (0.45, 0.035, 0.008),
            "tiktok": (0.65, 0.075, 0.018),
            "youtube_shorts": (0.55, 0.025, 0.006),
            "youtube": (0.35, 0.020, 0.005),
            "facebook": (0.30, 0.015, 0.004),
            "x": (0.40, 0.012, 0.008),
            "linkedin": (0.45, 0.018, 0.006),
        }

        base_completion, base_like, base_share = base_rates[platform]

        # Apply quality modifiers with realistic noise
        quality_multiplier = 0.5 + (quality_score / 100) * 0.8
        hook_multiplier = 0.8 + (hook_strength / 100) * 0.6
        trend_multiplier = 0.9 + (trend_score / 100) * 0.3

        # Add realistic noise (±20%)
        noise_factor = random.uniform(0.8, 1.2)

        completion = base_completion * quality_multiplier * hook_multiplier * trend_multiplier * noise_factor
        completion = max(0.01, min(0.99, completion))

        like_rate = base_like * quality_multiplier * trend_multiplier * noise_factor * random.uniform(0.7, 1.4)
        like_rate = max(0.001, min(0.25, like_rate))

        share_rate = base_share * quality_multiplier * originality/10 * noise_factor * random.uniform(0.6, 1.6)
        share_rate = max(0.0001, min(0.15, share_rate))

        # Skip rates (inverse relationship with completion, with platform-specific availability)
        skip_base = 1.0 - completion
        skip_3s = skip_base * random.uniform(0.2, 0.6)
        skip_10s = skip_base * random.uniform(0.4, 0.8)
        skip_30s = skip_base * random.uniform(0.6, 0.95)

        # Virality score with realistic calculation
        virality = (completion * 25 + like_rate * 20 + share_rate * 15 +
                   trend_score * 0.1 + competitor_engagement * 0.05)
        virality = min(95.0, virality)

        sample = {
            "script": f"Sample content about {random.choice(['technology', 'lifestyle', 'business', 'health', 'entertainment'])} in {language}",
            "hooks": random.sample(hooks, num_hooks) if num_hooks > 0 else [],
            "hashtags": random.sample(hashtags, num_hashtags) if num_hashtags > 0 else [],
            "ctas": random.sample(ctas, num_ctas) if num_ctas > 0 else [],
            "platform": platform,
            "duration_s": duration,
            "trend_score": trend_score,
            "language": language,
            "posting_hour": posting_hour,
            "competitor_engagement": competitor_engagement,
            "account_followers": account_followers,
            "has_trending_audio": has_trending_audio,
            "seasonal_trend": seasonal_trend,
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


def train_models_realistic(training_data):
    """Train ML models with realistic parameters"""

    # Prepare training data
    X = []
    y = {metric: [] for metric in ["completion_rate", "like_rate", "share_rate", "skip_3s", "skip_10s", "skip_30s", "virality"]}

    for sample in training_data:
        features = extract_features(sample)
        X.append(features)

        # Extract target values
        for metric in y.keys():
            if metric in sample:
                y[metric].append(sample[metric])

    X = np.array(X)

    # Fit scaler
    scaler = StandardScaler()
    scaler.fit(X)

    # Train models with realistic parameters to prevent overfitting
    results = {}
    for metric in y.keys():
        if len(y[metric]) >= 20:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y[metric], test_size=0.2, random_state=42
            )

            # Choose model type with conservative parameters
            if metric == "virality":
                model = GradientBoostingRegressor(
                    n_estimators=30,  # Conservative to prevent overfitting
                    max_depth=3,
                    learning_rate=0.05,  # Lower learning rate
                    min_samples_split=10,
                    random_state=42
                )
            else:
                model = RandomForestRegressor(
                    n_estimators=30,  # Conservative
                    max_depth=4,      # Shallow trees
                    min_samples_split=8,
                    min_samples_leaf=4,
                    random_state=42
                )

            model.fit(X_train, y_train)

            # Evaluate
            y_pred = model.predict(X_test)
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)

            # Save model
            model_path = MODEL_DIR / f"{metric.replace('_', '')}_{'gb' if metric == 'virality' else 'rf'}.pkl"
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

    # Save model version info
    import datetime
    version_info = {
        "last_trained": datetime.datetime.now().isoformat(),
        "training_samples": len(X),
        "data_source": "realistic_synthetic",
        "performance": results,
        "feature_count": len(FEATURE_NAMES),
        "features": FEATURE_NAMES,
        "notes": "Trained with conservative parameters to prevent overfitting. Realistic noise added to simulate real-world data."
    }
    with open(MODEL_DIR / "model_versions.json", 'w') as f:
        json.dump(version_info, f, indent=2)

    return {
        "trained_metrics": list(results.keys()),
        "performance": results,
        "total_samples": len(X),
        "models_saved": len(results),
        "data_source": "realistic_synthetic",
        "feature_count": len(FEATURE_NAMES)
    }


def main():
    print("🎯 Training Realistic Engagement Prediction Models")
    print("=" * 60)

    # Generate realistic training data
    print("📊 Generating realistic training data...")
    training_data = generate_realistic_training_data(1500)
    print(f"✅ Generated {len(training_data)} training samples")

    # Save sample data for inspection
    sample_file = MODEL_DIR / "realistic_training_sample.json"
    with open(sample_file, 'w') as f:
        json.dump(training_data[:3], f, indent=2)
    print(f"💾 Saved sample training data to {sample_file}")

    # Train models
    print("\n🤖 Training ML models with realistic parameters...")
    results = train_models_realistic(training_data)

    print("✅ Training completed!")
    print(f"📈 Trained {results['models_saved']} models on {results['total_samples']} samples")

    print("\n📊 Model Performance (Realistic Expectations):")
    for metric, perf in results['performance'].items():
        print(f"  {metric}: MAE={perf['mae']:.4f}, R²={perf['r2_score']:.4f} ({perf['samples']} samples)")

    print("\n✅ Models are now trained with realistic parameters!")
    print("💡 These models should perform better on real data than the previous overfitted ones.")
    print("🔄 Ready for real engagement data collection and retraining.")


if __name__ == "__main__":
    main()