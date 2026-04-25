"""
EngagementPredictionEngine — ML-based prediction of engagement metrics.

Uses trained models (Random Forest/Gradient Boosting) for:
- Completion rate prediction
- Like rate prediction
- Share rate prediction
- Skip rate at 3s, 10s, 30s intervals (where available)
- Virality probability

Features: 26-dimensional feature vector with quality signals, platform data,
temporal features, social context, and language support.

Models trained on historical engagement data with realistic performance metrics.
"""

from __future__ import annotations

import json
import os
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler

from app.engines.base import BaseEngine
from app.engines.quality.quality_engine import QualityEngine

# Model storage
MODEL_DIR = Path(__file__).parent.parent.parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

PLATFORM_ENCODER = {
    "instagram": 0, "tiktok": 1, "youtube_shorts": 2, "youtube": 3,
    "facebook": 4, "x": 5, "linkedin": 6, "telegram": 7
}

LANGUAGE_ENCODER = {
    "english": 0, "hindi": 1, "spanish": 2, "french": 3,
    "german": 4, "arabic": 5, "portuguese": 6, "other": 7
}

# Platform-specific data availability for skip rates
PLATFORM_SKIP_DATA_AVAILABILITY = {
    "youtube": {"skip_3s": True, "skip_10s": True, "skip_30s": True},  # Detailed analytics
    "youtube_shorts": {"skip_3s": True, "skip_10s": True, "skip_30s": True},
    "tiktok": {"skip_3s": False, "skip_10s": False, "skip_30s": False},  # No granular data
    "instagram": {"skip_3s": False, "skip_10s": False, "skip_30s": False},  # Limited analytics
    "facebook": {"skip_3s": False, "skip_10s": False, "skip_30s": False},
    "x": {"skip_3s": False, "skip_10s": False, "skip_30s": False},
    "linkedin": {"skip_3s": False, "skip_10s": False, "skip_30s": False},
}

# Feature names for transparency (26 features)
FEATURE_NAMES = [
    "script_length",           # 0: Length of script text
    "word_count",              # 1: Number of words
    "sentence_count",          # 2: Number of sentences
    "hook_count",              # 3: Number of hooks
    "avg_hook_length",         # 4: Average hook length
    "hook_power_words",        # 5: Count of power words in hooks
    "hashtag_count",           # 6: Number of hashtags
    "hashtag_diversity",       # 7: Hashtag diversity ratio
    "cta_count",               # 8: Number of CTAs
    "cta_strength",            # 9: CTA strength score
    "quality_score",           # 10: Overall quality score (0-100)
    "hook_strength",           # 11: Hook strength (0-100)
    "engagement_signals",      # 12: Engagement signals count
    "originality",             # 13: Originality score
    "platform_encoded",        # 14: Platform as numeric code
    "duration_s",              # 15: Video duration in seconds
    "duration_factor",         # 16: Optimal duration factor
    "trend_score",             # 17: Trend score (0-100)
    "language_encoded",        # 18: Language as numeric code
    "hour_of_day",             # 19: Hour when content is posted
    "day_of_week",             # 20: Day of week (0-6)
    "is_weekend",              # 21: Boolean for weekend posting
    "competitor_avg_engagement", # 22: Average engagement of similar content
    "account_followers_log",   # 23: Log of account followers
    "has_trending_audio",      # 24: Boolean for trending audio
    "seasonal_trend_factor",   # 25: Seasonal trend multiplier
]


class EngagementPredictionEngine(BaseEngine):
    name = "engagement_prediction"
    description = "ML-based engagement and skip rate prediction with transparency"

    def __init__(self) -> None:
        super().__init__()
        self.quality_engine = QualityEngine()
        self.models = self._load_models()
        self.scaler = self._load_scaler()
        self.is_trained = self._check_if_trained()
        self.model_versions = self._load_model_versions()

    def _load_models(self) -> Dict[str, Any]:
        """Load trained ML models"""
        models = {}
        model_files = {
            "completion_rate": "completion_rf.pkl",
            "like_rate": "like_rf.pkl",
            "share_rate": "share_rf.pkl",
            "skip_3s": "skip_3s_rf.pkl",
            "skip_10s": "skip_10s_rf.pkl",
            "skip_30s": "skip_30s_rf.pkl",
            "virality": "virality_gb.pkl"
        }

        for metric, filename in model_files.items():
            model_path = MODEL_DIR / filename
            if model_path.exists():
                with open(model_path, 'rb') as f:
                    models[metric] = pickle.load(f)
            else:
                # Fallback to simple baseline models if not trained
                models[metric] = self._create_baseline_model()

        return models

    def _load_scaler(self) -> StandardScaler:
        """Load feature scaler"""
        scaler_path = MODEL_DIR / "feature_scaler.pkl"
        if scaler_path.exists():
            with open(scaler_path, 'rb') as f:
                return pickle.load(f)
        else:
            return StandardScaler()

    def _load_model_versions(self) -> Dict[str, Any]:
        """Load model version information"""
        version_path = MODEL_DIR / "model_versions.json"
        if version_path.exists():
            with open(version_path, 'r') as f:
                return json.load(f)
        return {
            "last_trained": None,
            "training_samples": 0,
            "data_source": "synthetic",
            "performance": {}
        }

    def _check_if_trained(self) -> bool:
        """Check if models are properly trained"""
        return all(isinstance(model, (RandomForestRegressor, GradientBoostingRegressor))
                  for model in self.models.values())

    def _create_baseline_model(self):
        """Create simple baseline model for untrained metrics"""
        from sklearn.dummy import DummyRegressor
        return DummyRegressor(strategy="mean")

    def run(
        self,
        *,
        script: str,
        hooks: Optional[List[str]] = None,
        hashtags: Optional[List[str]] = None,
        ctas: Optional[List[str]] = None,
        platform: str = "instagram",
        duration_s: float = 30.0,
        trend_score: float = 0.0,
        language: str = "english",
        posting_hour: Optional[int] = None,
        competitor_engagement: float = 0.0,
        account_followers: int = 1000,
        has_trending_audio: bool = False,
        seasonal_trend: float = 1.0,
    ) -> Dict[str, Any]:
        """Predict engagement metrics using ML models"""

        # Get quality analysis
        quality_data = self.quality_engine.run(
            script=script, hooks=hooks, hashtags=hashtags, ctas=ctas
        )

        # Extract features for ML model
        features = self._extract_features(
            script=script,
            hooks=hooks or [],
            hashtags=hashtags or [],
            ctas=ctas or [],
            platform=platform,
            duration_s=duration_s,
            trend_score=trend_score,
            quality_data=quality_data,
            language=language,
            posting_hour=posting_hour,
            competitor_engagement=competitor_engagement,
            account_followers=account_followers,
            has_trending_audio=has_trending_audio,
            seasonal_trend=seasonal_trend
        )

        # Scale features
        features_scaled = self.scaler.transform([features])[0] if hasattr(self.scaler, 'transform') else features

        # Make predictions
        predictions = {}
        for metric, model in self.models.items():
            try:
                pred = model.predict([features_scaled])[0]
                # Ensure predictions are within reasonable bounds
                pred = self._clamp_prediction(metric, pred)
                predictions[metric] = round(float(pred), 4)
            except Exception as e:
                self.logger.warning(f"Prediction failed for {metric}: {e}")
                predictions[metric] = self._get_fallback_value(metric)

        # Calculate derived metrics
        completion_rate = predictions.get("completion_rate", 0.5)
        expected_watch_seconds = round(duration_s * completion_rate, 2)

        # Virality score (weighted combination)
        virality_components = {
            "completion": completion_rate * 0.25,
            "likes": predictions.get("like_rate", 0.03) * 0.20,
            "shares": predictions.get("share_rate", 0.008) * 0.15,
            "trend_bonus": min(trend_score / 100, 0.15),
            "competitor_bonus": min(competitor_engagement / 100, 0.10),
            "seasonal_bonus": min((seasonal_trend - 1) * 0.15, 0.15)
        }
        virality_score = sum(virality_components.values()) * 100

        # Check skip rate data availability
        skip_data_available = PLATFORM_SKIP_DATA_AVAILABILITY.get(platform, {"skip_3s": False, "skip_10s": False, "skip_30s": False})

        return {
            "platform": platform,
            "language": language,
            "model_trained": self.is_trained,
            "data_source": self.model_versions.get("data_source", "synthetic"),
            "predictions": {
                "completion_rate": predictions.get("completion_rate", 0.5),
                "like_rate": predictions.get("like_rate", 0.03),
                "share_rate": predictions.get("share_rate", 0.008),
                "skip_rate_3s": predictions.get("skip_3s", 0.15) if skip_data_available["skip_3s"] else None,
                "skip_rate_10s": predictions.get("skip_10s", 0.35) if skip_data_available["skip_10s"] else None,
                "skip_rate_30s": predictions.get("skip_30s", 0.60) if skip_data_available["skip_30s"] else None,
                "virality_probability": round(min(virality_score, 99.0), 2),
            },
            "expected_watch_seconds": expected_watch_seconds,
            "quality_score": quality_data.get("score", 0),
            "virality_breakdown": virality_components,
            "features_used": len(features),
            "skip_data_available": skip_data_available,
            "feature_importance": self._get_feature_importance() if self.is_trained else None,
            "notes": f"ML-based predictions using {self.model_versions.get('data_source', 'synthetic')} data. "
                     f"Trained on {self.model_versions.get('training_samples', 0)} samples. "
                     f"Skip rates: {'Available' if any(skip_data_available.values()) else 'Not available'} for {platform}"
        }

    def _extract_features(self, script: str, hooks: List[str], hashtags: List[str],
                         ctas: List[str], platform: str, duration_s: float,
                         trend_score: float, quality_data: Dict[str, Any],
                         language: str, posting_hour: Optional[int],
                         competitor_engagement: float, account_followers: int,
                         has_trending_audio: bool, seasonal_trend: float) -> List[float]:
        """Extract 26-dimensional numerical features for ML model"""

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
        duration_factor = 1.0 - abs(duration_s - 30) / 60  # Optimal around 30s

        # Language features
        language_encoded = LANGUAGE_ENCODER.get(language.lower(), 7)  # 'other' as default

        # Temporal features
        current_hour = posting_hour if posting_hour is not None else datetime.now().hour
        current_day = datetime.now().weekday()
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

    def _clamp_prediction(self, metric: str, value: float) -> float:
        """Ensure predictions are within reasonable bounds"""
        bounds = {
            "completion_rate": (0.01, 0.99),
            "like_rate": (0.001, 0.25),
            "share_rate": (0.0001, 0.15),
            "skip_3s": (0.01, 0.50),
            "skip_10s": (0.05, 0.80),
            "skip_30s": (0.10, 0.95),
            "virality": (0.0, 100.0)
        }
        min_val, max_val = bounds.get(metric, (0.0, 1.0))
        return max(min_val, min(max_val, value))

    def _get_fallback_value(self, metric: str) -> float:
        """Fallback values when model prediction fails"""
        fallbacks = {
            "completion_rate": 0.55,
            "like_rate": 0.05,
            "share_rate": 0.012,
            "skip_3s": 0.15,
            "skip_10s": 0.35,
            "skip_30s": 0.60,
            "virality": 25.0
        }
        return fallbacks.get(metric, 0.5)

    def _get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from trained models"""
        if not self.is_trained:
            return {}

        # Use completion rate model as representative
        model = self.models.get("completion_rate")
        if hasattr(model, 'feature_importances_'):
            importance_scores = model.feature_importances_
            return {FEATURE_NAMES[i]: round(float(score), 4)
                   for i, score in enumerate(importance_scores)}
        return {}

    def train_models(self, training_data: List[Dict[str, Any]], data_source: str = "real") -> Dict[str, Any]:
        """Train ML models on historical engagement data"""

        if len(training_data) < 50:
            return {"error": "Need at least 50 training samples"}

        # Prepare training data
        X = []
        y = {metric: [] for metric in self.models.keys()}

        for sample in training_data:
            features = self._extract_features(
                script=sample.get("script", ""),
                hooks=sample.get("hooks", []),
                hashtags=sample.get("hashtags", []),
                ctas=sample.get("ctas", []),
                platform=sample.get("platform", "instagram"),
                duration_s=sample.get("duration_s", 30.0),
                trend_score=sample.get("trend_score", 0.0),
                quality_data=sample.get("quality_data", {}),
                language=sample.get("language", "english"),
                posting_hour=sample.get("posting_hour"),
                competitor_engagement=sample.get("competitor_engagement", 0.0),
                account_followers=sample.get("account_followers", 1000),
                has_trending_audio=sample.get("has_trending_audio", False),
                seasonal_trend=sample.get("seasonal_trend", 1.0)
            )
            X.append(features)

            # Extract target values
            for metric in y.keys():
                if metric in sample:
                    y[metric].append(sample[metric])
                else:
                    # Skip samples missing target metrics
                    break
            else:
                continue
            break  # Only add if all metrics present

        if len(X) < 20:
            return {"error": "Insufficient complete training samples"}

        X = np.array(X)

        # Fit scaler
        self.scaler.fit(X)

        # Train models with realistic parameters to prevent overfitting
        results = {}
        for metric in y.keys():
            if len(y[metric]) >= 20:
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y[metric], test_size=0.2, random_state=42
                )

                # Choose model type with realistic parameters
                if metric == "virality":
                    model = GradientBoostingRegressor(
                        n_estimators=50,  # Reduced to prevent overfitting
                        max_depth=3,
                        learning_rate=0.1,
                        random_state=42
                    )
                else:
                    model = RandomForestRegressor(
                        n_estimators=50,  # Reduced to prevent overfitting
                        max_depth=5,
                        min_samples_split=5,
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

                self.models[metric] = model
                results[metric] = {
                    "mae": round(mae, 4),
                    "r2_score": round(r2, 4),
                    "samples": len(y_train) + len(y_test)
                }

        # Save scaler
        with open(MODEL_DIR / "feature_scaler.pkl", 'wb') as f:
            pickle.dump(self.scaler, f)

        # Save model version info
        version_info = {
            "last_trained": datetime.now().isoformat(),
            "training_samples": len(X),
            "data_source": data_source,
            "performance": results,
            "feature_count": len(FEATURE_NAMES),
            "features": FEATURE_NAMES
        }
        with open(MODEL_DIR / "model_versions.json", 'w') as f:
            json.dump(version_info, f, indent=2)

        self.is_trained = True
        self.model_versions = version_info

        return {
            "trained_metrics": list(results.keys()),
            "performance": results,
            "total_samples": len(X),
            "models_saved": len(results),
            "data_source": data_source,
            "feature_count": len(FEATURE_NAMES)
        }

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about trained engagement prediction models"""
        return {
            "is_trained": self.is_trained,
            "available_models": list(self.models.keys()),
            "model_types": {k: type(v).__name__ for k, v in self.models.items()},
            "feature_count": len(FEATURE_NAMES),
            "features": FEATURE_NAMES,
            "supported_platforms": list(PLATFORM_ENCODER.keys()),
            "supported_languages": list(LANGUAGE_ENCODER.keys()),
            "platform_skip_data_availability": PLATFORM_SKIP_DATA_AVAILABILITY,
            "model_versions": self.model_versions,
            "data_source": self.model_versions.get("data_source", "unknown"),
            "last_trained": self.model_versions.get("last_trained"),
            "training_samples": self.model_versions.get("training_samples", 0)
        }

    def collect_real_engagement_data(self, post_id: int, actual_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Collect real engagement data for future retraining"""

        data_path = MODEL_DIR / "real_engagement_data.jsonl"
        data_path.parent.mkdir(exist_ok=True)

        # Load existing data
        existing_data = []
        if data_path.exists():
            with open(data_path, 'r') as f:
                for line in f:
                    if line.strip():
                        existing_data.append(json.loads(line))

        # Add new data point
        data_point = {
            "post_id": post_id,
            "collected_at": datetime.now().isoformat(),
            "metrics": actual_metrics
        }
        existing_data.append(data_point)

        # Save updated data
        with open(data_path, 'w') as f:
            for item in existing_data:
                f.write(json.dumps(item) + '\n')

        return {
            "message": "Real engagement data collected",
            "total_samples": len(existing_data),
            "latest_metrics": actual_metrics
        }

    def get_real_data_stats(self) -> Dict[str, Any]:
        """Get statistics about collected real engagement data"""

        data_path = MODEL_DIR / "real_engagement_data.jsonl"
        if not data_path.exists():
            return {"total_samples": 0, "platforms": [], "date_range": None}

        data = []
        with open(data_path, 'r') as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))

        if not data:
            return {"total_samples": 0, "platforms": [], "date_range": None}

        platforms = list(set(d["metrics"].get("platform", "unknown") for d in data))
        dates = [d["collected_at"] for d in data]
        date_range = {"earliest": min(dates), "latest": max(dates)} if dates else None

        return {
            "total_samples": len(data),
            "platforms": platforms,
            "date_range": date_range,
            "ready_for_retraining": len(data) >= 100
        }

    def _load_models(self) -> Dict[str, Any]:
        """Load trained ML models"""
        models = {}
        model_files = {
            "completion_rate": "completion_rf.pkl",
            "like_rate": "like_rf.pkl",
            "share_rate": "share_rf.pkl",
            "skip_3s": "skip_3s_rf.pkl",
            "skip_10s": "skip_10s_rf.pkl",
            "skip_30s": "skip_30s_rf.pkl",
            "virality": "virality_gb.pkl"
        }

        for metric, filename in model_files.items():
            model_path = MODEL_DIR / filename
            if model_path.exists():
                with open(model_path, 'rb') as f:
                    models[metric] = pickle.load(f)
            else:
                # Fallback to simple baseline models if not trained
                models[metric] = self._create_baseline_model()

        return models

    def _load_scaler(self) -> StandardScaler:
        """Load feature scaler"""
        scaler_path = MODEL_DIR / "feature_scaler.pkl"
        if scaler_path.exists():
            with open(scaler_path, 'rb') as f:
                return pickle.load(f)
        else:
            return StandardScaler()

    def _check_if_trained(self) -> bool:
        """Check if models are properly trained"""
        return all(isinstance(model, (RandomForestRegressor, GradientBoostingRegressor))
                  for model in self.models.values())

    def _create_baseline_model(self):
        """Create simple baseline model for untrained metrics"""
        from sklearn.dummy import DummyRegressor
        return DummyRegressor(strategy="mean")

    def run(
        self,
        *,
        script: str,
        hooks: Optional[List[str]] = None,
        hashtags: Optional[List[str]] = None,
        ctas: Optional[List[str]] = None,
        platform: str = "instagram",
        duration_s: float = 30.0,
        trend_score: float = 0.0,
    ) -> Dict[str, Any]:
        """Predict engagement metrics using ML models"""

        # Get quality analysis
        quality_data = self.quality_engine.run(
            script=script, hooks=hooks, hashtags=hashtags, ctas=ctas
        )

        # Extract features for ML model
        features = self._extract_features(
            script=script,
            hooks=hooks or [],
            hashtags=hashtags or [],
            ctas=ctas or [],
            platform=platform,
            duration_s=duration_s,
            trend_score=trend_score,
            quality_data=quality_data
        )

        # Scale features
        features_scaled = self.scaler.transform([features])[0] if hasattr(self.scaler, 'transform') else features

        # Make predictions
        predictions = {}
        for metric, model in self.models.items():
            try:
                pred = model.predict([features_scaled])[0]
                # Ensure predictions are within reasonable bounds
                pred = self._clamp_prediction(metric, pred)
                predictions[metric] = round(float(pred), 4)
            except Exception as e:
                self.logger.warning(f"Prediction failed for {metric}: {e}")
                predictions[metric] = self._get_fallback_value(metric)

        # Calculate derived metrics
        completion_rate = predictions.get("completion_rate", 0.5)
        expected_watch_seconds = round(duration_s * completion_rate, 2)

        # Virality score (weighted combination)
        virality_components = {
            "completion": completion_rate * 0.3,
            "likes": predictions.get("like_rate", 0.03) * 0.25,
            "shares": predictions.get("share_rate", 0.008) * 0.25,
            "trend_bonus": min(trend_score / 100, 0.2)  # Bonus for trending topics
        }
        virality_score = sum(virality_components.values()) * 100

        return {
            "platform": platform,
            "model_trained": self.is_trained,
            "predictions": {
                "completion_rate": predictions.get("completion_rate", 0.5),
                "like_rate": predictions.get("like_rate", 0.03),
                "share_rate": predictions.get("share_rate", 0.008),
                "skip_rate_3s": predictions.get("skip_3s", 0.15),
                "skip_rate_10s": predictions.get("skip_10s", 0.35),
                "skip_rate_30s": predictions.get("skip_30s", 0.60),
                "virality_probability": round(min(virality_score, 99.0), 2),
            },
            "expected_watch_seconds": expected_watch_seconds,
            "quality_score": quality_data.get("score", 0),
            "virality_breakdown": virality_components,
            "features_used": len(features),
            "notes": "ML-based predictions using trained models on historical data" if self.is_trained
                    else "Using baseline predictions - models not yet trained on real data"
        }

    def _extract_features(self, script: str, hooks: List[str], hashtags: List[str],
                         ctas: List[str], platform: str, duration_s: float,
                         trend_score: float, quality_data: Dict[str, Any]) -> List[float]:
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

    def _clamp_prediction(self, metric: str, value: float) -> float:
        """Ensure predictions are within reasonable bounds"""
        bounds = {
            "completion_rate": (0.01, 0.99),
            "like_rate": (0.001, 0.25),
            "share_rate": (0.0001, 0.15),
            "skip_3s": (0.01, 0.50),
            "skip_10s": (0.05, 0.80),
            "skip_30s": (0.10, 0.95),
            "virality": (0.0, 100.0)
        }
        min_val, max_val = bounds.get(metric, (0.0, 1.0))
        return max(min_val, min(max_val, value))

    def _get_fallback_value(self, metric: str) -> float:
        """Fallback values when model prediction fails"""
        fallbacks = {
            "completion_rate": 0.55,
            "like_rate": 0.05,
            "share_rate": 0.012,
            "skip_3s": 0.15,
            "skip_10s": 0.35,
            "skip_30s": 0.60,
            "virality": 25.0
        }
        return fallbacks.get(metric, 0.5)

    def train_models(self, training_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Train ML models on historical engagement data"""

        if len(training_data) < 50:
            return {"error": "Need at least 50 training samples"}

        # Prepare training data
        X = []
        y = {metric: [] for metric in self.models.keys()}

        for sample in training_data:
            features = self._extract_features(
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
                else:
                    # Skip samples missing target metrics
                    break
            else:
                continue
            break  # Only add if all metrics present

        if len(X) < 20:
            return {"error": "Insufficient complete training samples"}

        X = np.array(X)

        # Fit scaler
        self.scaler.fit(X)

        # Train models
        results = {}
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
                model_path = MODEL_DIR / f"{metric.replace('_', '')}_{'gb' if metric == 'virality' else 'rf'}.pkl"
                with open(model_path, 'wb') as f:
                    pickle.dump(model, f)

                self.models[metric] = model
                results[metric] = {
                    "mae": round(mae, 4),
                    "r2_score": round(r2, 4),
                    "samples": len(y_train) + len(y_test)
                }

        # Save scaler
        with open(MODEL_DIR / "feature_scaler.pkl", 'wb') as f:
            pickle.dump(self.scaler, f)

        self.is_trained = True

        return {
            "trained_metrics": list(results.keys()),
            "performance": results,
            "total_samples": len(X),
            "models_saved": len(results)
        }

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about trained models"""
        return {
            "is_trained": self.is_trained,
            "available_models": list(self.models.keys()),
            "model_types": {k: type(v).__name__ for k, v in self.models.items()},
            "feature_count": 18,  # Number of features extracted
            "supported_platforms": list(PLATFORM_ENCODER.keys())
        }
