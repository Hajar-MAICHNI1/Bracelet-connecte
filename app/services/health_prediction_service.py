from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session
import logging
import joblib
import numpy as np
import os

from app.models.enums import MetricType
from app.repositories.metric_repository import MetricRepository
from app.schemas.health_prediction import (
    HealthPredictionRequest,
    HealthPredictionResponse,
    HealthRiskLevel
)
from app.core.exceptions import UserNotFoundException

# Configure logging
logger = logging.getLogger(__name__)


class HealthPredictionService:
    """Simplified service for health status prediction based on SpO2 metrics."""
    
    def __init__(self, db: Session):
        self.db = db
        self.metric_repo = MetricRepository(db)
        
        # Load ML model
        self.ml_model = self._load_ml_model()
        
        # Simple risk level thresholds
        self.risk_thresholds = {
            HealthRiskLevel.LOW: 0.8,    # Score >= 0.8
            HealthRiskLevel.MEDIUM: 0.6,  # Score >= 0.6
            HealthRiskLevel.HIGH: 0.0,    # Score < 0.6
        }

    def _load_ml_model(self):
        """
        Load the ML model from the joblib file.
        
        Returns:
            Loaded ML model
        """
        try:
            model_path = os.path.join(os.path.dirname(__file__), '..', 'ml', 'model_spo2_rf.joblib')
            model = joblib.load(model_path)
            logger.info("ML model loaded successfully")
            return model
        except Exception as e:
            logger.error(f"Failed to load ML model: {e}")
            raise RuntimeError(f"Failed to load ML model: {e}")

    def _get_spo2_data(self, user_id: str) -> Optional[float]:
        """
        Get SpO2 metrics from the database for the last 24 hours.
        
        Args:
            user_id: User ID to get data for
            
        Returns:
            Average SpO2 value or None if no data
        """
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=24)
            
            # Get SpO2 metrics for the last 24 hours
            metrics = self.metric_repo.get_user_metrics(
                user_id=user_id,
                metric_type=MetricType.SPO2,
                start_date=start_time,
                end_date=end_time
            )
            
            # Filter metrics with values and calculate average
            metrics_with_values = [m for m in metrics if m.value is not None]
            
            if metrics_with_values:
                values = [m.value for m in metrics_with_values]
                average_value = sum(values) / len(values)
                logger.info(f"Found {len(values)} SpO2 data points, average: {average_value}")
                return average_value
            else:
                logger.warning(f"No SpO2 data found for user {user_id} in last 24 hours")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get SpO2 data for user {user_id}: {e}")
            return None

    def _predict_with_model(self, spo2_value: float) -> float:
        """
        Make prediction using the loaded model with SpO2 data.
        
        Args:
            spo2_value: SpO2 value to predict with
            
        Returns:
            Health score (higher is better)
        """
        try:
            # Create feature array for the model
            features = np.array([[spo2_value]])
            
            # Make prediction
            prediction = self.ml_model.predict(features)
            
            # Assuming the model predicts health risk (0 = healthy, 1 = at risk)
            # Convert to health score (higher is better)
            if len(prediction) > 0:
                health_risk = prediction[0]
                health_score = 1.0 - health_risk
                return float(health_score)
            else:
                return 0.5  # Default neutral score
                
        except Exception as e:
            logger.error(f"ML model prediction failed: {e}")
            return 0.5  # Default neutral score on error

    def predict_health_status(self, request: HealthPredictionRequest) -> HealthPredictionResponse:
        """
        Predict health status based on last 24 hours of SpO2 metrics.
        
        Args:
            request: Health prediction request
            
        Returns:
            Health prediction response with score and risk level
        """
        logger.info(f"Starting health prediction for user {request.user_id}")
        
        try:
            # Get SpO2 data from database
            spo2_value = self._get_spo2_data(request.user_id)
            
            if spo2_value is None:
                # No data available - return neutral prediction
                overall_health_score = 0.5
                health_risk_level = HealthRiskLevel.MEDIUM
                logger.warning(f"No SpO2 data available for user {request.user_id}")
            else:
                # Make prediction using ML model
                overall_health_score = self._predict_with_model(spo2_value)
                
                # Determine health risk level
                if overall_health_score >= self.risk_thresholds[HealthRiskLevel.LOW]:
                    health_risk_level = HealthRiskLevel.LOW
                elif overall_health_score >= self.risk_thresholds[HealthRiskLevel.MEDIUM]:
                    health_risk_level = HealthRiskLevel.MEDIUM
                else:
                    health_risk_level = HealthRiskLevel.HIGH
                
                logger.info(f"Prediction completed: score={overall_health_score:.2f}, risk={health_risk_level.value}")

            response = HealthPredictionResponse(
                user_id=request.user_id,
                prediction_timestamp=datetime.now(timezone.utc),
                overall_health_score=overall_health_score,
                health_risk_level=health_risk_level,
                confidence_score=1.0,  # Simple confidence since we're using ML model directly
                metric_averages=[],  # Empty since we're not calculating multiple metrics
                risk_factors=[],  # Empty since we're not generating complex risk factors
                recommendations=[],  # Empty since we're not generating recommendations
                raw_metrics_summary=None,  # Empty since we're not including detailed metrics
                model_version="v2.0.0-simplified-ml",
                prediction_horizon_hours=request.prediction_horizon_hours or 24
            )
            
            return response
            
        except UserNotFoundException:
            logger.error(f"User not found for health prediction: {request.user_id}")
            raise
        except Exception as e:
            logger.error(f"Health prediction failed for user {request.user_id}: {e}")
            raise