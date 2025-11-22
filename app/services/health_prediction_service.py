from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
import logging
import statistics

from app.models.enums import MetricType
from app.repositories.metric_repository import MetricRepository
from app.schemas.health_prediction import (
    HealthPredictionRequest,
    HealthPredictionResponse,
    HealthRiskLevel,
    MetricAverage
)
from app.core.exceptions import UserNotFoundException, MetricNotFoundException


# Configure logging
logger = logging.getLogger(__name__)


class HealthPredictionService:
    """Service for health status prediction based on metrics data."""
    
    def __init__(self, db: Session):
        self.db = db
        self.metric_repo = MetricRepository(db)
        
        # Define healthy ranges for each metric type based on medical guidelines
        self.healthy_ranges = {
            MetricType.HEART_RATE: (60.0, 100.0),  # BPM
            MetricType.SPO2: (95.0, 100.0),        # Percentage
            MetricType.SLEEP: (7.0, 9.0),          # Hours
            MetricType.STEPS: (8000.0, 25000.0),   # Steps per day
            MetricType.SKIN_TEMPERATURE: (36.5, 37.5),  # Celsius
            MetricType.AMBIENT_TEMPERATURE: (18.0, 24.0),  # Celsius (comfortable range)
        }
        
        # Define metric units
        self.metric_units = {
            MetricType.HEART_RATE: "BPM",
            MetricType.SPO2: "%",
            MetricType.SLEEP: "hours",
            MetricType.STEPS: "steps",
            MetricType.SKIN_TEMPERATURE: "°C",
            MetricType.AMBIENT_TEMPERATURE: "°C",
        }
        
        # Model configuration
        self.model_version = "v1.0.0-rule-based"
        self.min_data_points_for_confidence = 5
        
        # Risk level thresholds
        self.risk_thresholds = {
            HealthRiskLevel.LOW: 0.8,    # Score >= 0.8
            HealthRiskLevel.MEDIUM: 0.6,  # Score >= 0.6
            HealthRiskLevel.HIGH: 0.0,    # Score < 0.6
        }

    def _calculate_24h_averages(self, user_id: str) -> Dict[MetricType, Dict]:
        """
        Calculate 24-hour averages for all metric types.
        
        Args:
            user_id: User ID to calculate averages for
            
        Returns:
            Dictionary with metric type as key and average data as value
        """
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=24)
        
        averages = {}
        
        for metric_type in MetricType:
            try:
                # Get metrics for the last 24 hours
                metrics = self.metric_repo.get_user_metrics(
                    user_id=user_id,
                    metric_type=metric_type,
                    start_date=start_time,
                    end_date=end_time
                )
                
                # Filter metrics with values
                metrics_with_values = [m for m in metrics if m.value is not None]
                
                if metrics_with_values:
                    values = [m.value for m in metrics_with_values]
                    average_value = statistics.mean(values)
                    data_points = len(values)
                    
                    averages[metric_type] = {
                        'average_value': average_value,
                        'data_points': data_points,
                        'unit': self.metric_units.get(metric_type, "unknown"),
                        'raw_metrics': metrics_with_values
                    }
                else:
                    averages[metric_type] = {
                        'average_value': None,
                        'data_points': 0,
                        'unit': self.metric_units.get(metric_type, "unknown"),
                        'raw_metrics': []
                    }
                    
            except Exception as e:
                logger.warning(f"Failed to calculate average for {metric_type}: {e}")
                averages[metric_type] = {
                    'average_value': None,
                    'data_points': 0,
                    'unit': self.metric_units.get(metric_type, "unknown"),
                    'raw_metrics': []
                }
        
        return averages

    def _calculate_metric_health_score(self, metric_type: MetricType, average_value: Optional[float]) -> Tuple[bool, float]:
        """
        Calculate health score for a single metric.
        
        Args:
            metric_type: Type of metric
            average_value: Average value of the metric
            
        Returns:
            Tuple of (is_healthy, health_score)
        """
        if average_value is None:
            return False, 0.0
            
        if metric_type not in self.healthy_ranges:
            return True, 0.5  # Default score for unknown metrics
            
        min_healthy, max_healthy = self.healthy_ranges[metric_type]
        
        # Calculate how far from ideal range (0 = perfect, 1 = very bad)
        if min_healthy <= average_value <= max_healthy:
            # Within healthy range - perfect score
            return True, 1.0
        else:
            # Outside healthy range - calculate penalty
            if average_value < min_healthy:
                distance = min_healthy - average_value
                range_size = max_healthy - min_healthy
            else:
                distance = average_value - max_healthy
                range_size = max_healthy - min_healthy
                
            # Normalize distance and calculate score (0-1)
            normalized_distance = min(distance / range_size, 2.0)  # Cap at 2x range size
            score = max(0.0, 1.0 - normalized_distance)
            return False, score

    def _generate_risk_factors(self, metric_averages: List[MetricAverage]) -> List[str]:
        """
        Generate risk factors based on metric analysis.
        
        Args:
            metric_averages: List of metric averages with health scores
            
        Returns:
            List of risk factor descriptions
        """
        risk_factors = []
        
        for metric_avg in metric_averages:
            if not metric_avg.is_healthy:
                if metric_avg.metric_type == MetricType.HEART_RATE:
                    risk_factors.append(f"Abnormal heart rate ({metric_avg.average_value} {metric_avg.unit})")
                elif metric_avg.metric_type == MetricType.SPO2:
                    risk_factors.append(f"Low blood oxygen ({metric_avg.average_value} {metric_avg.unit})")
                elif metric_avg.metric_type == MetricType.SLEEP:
                    risk_factors.append(f"Inadequate sleep ({metric_avg.average_value} {metric_avg.unit})")
                elif metric_avg.metric_type == MetricType.STEPS:
                    risk_factors.append(f"Low physical activity ({metric_avg.average_value} {metric_avg.unit})")
                elif metric_avg.metric_type == MetricType.SKIN_TEMPERATURE:
                    risk_factors.append(f"Abnormal body temperature ({metric_avg.average_value} {metric_avg.unit})")
        
        return risk_factors

    def _generate_recommendations(self, metric_averages: List[MetricAverage]) -> List[str]:
        """
        Generate health recommendations based on metric analysis.
        
        Args:
            metric_averages: List of metric averages with health scores
            
        Returns:
            List of recommendation descriptions
        """
        recommendations = []
        
        for metric_avg in metric_averages:
            if not metric_avg.is_healthy:
                if metric_avg.metric_type == MetricType.HEART_RATE:
                    if metric_avg.average_value < 60:
                        recommendations.append("Consider consulting a doctor about low heart rate")
                    else:
                        recommendations.append("Consider stress management techniques for elevated heart rate")
                elif metric_avg.metric_type == MetricType.SPO2:
                    recommendations.append("Seek medical attention for low blood oxygen levels")
                elif metric_avg.metric_type == MetricType.SLEEP:
                    if metric_avg.average_value < 7:
                        recommendations.append("Aim for 7-9 hours of sleep per night")
                    else:
                        recommendations.append("Consider sleep quality improvement strategies")
                elif metric_avg.metric_type == MetricType.STEPS:
                    recommendations.append("Increase daily physical activity to 8,000+ steps")
                elif metric_avg.metric_type == MetricType.SKIN_TEMPERATURE:
                    recommendations.append("Monitor body temperature and consult if persistent")
        
        # Add general recommendations if no specific issues
        if not recommendations:
            recommendations.extend([
                "Maintain current healthy lifestyle habits",
                "Continue regular health monitoring"
            ])
        
        return recommendations

    def _calculate_confidence_score(self, metric_averages: List[MetricAverage]) -> float:
        """
        Calculate overall confidence score for the prediction.
        
        Args:
            metric_averages: List of metric averages with data points
            
        Returns:
            Confidence score between 0 and 1
        """
        if not metric_averages:
            return 0.0
            
        total_data_points = sum(ma.data_points for ma in metric_averages)
        metrics_with_data = sum(1 for ma in metric_averages if ma.data_points > 0)
        total_metrics = len(metric_averages)
        
        # Confidence based on data availability
        data_coverage = metrics_with_data / total_metrics if total_metrics > 0 else 0.0
        data_density = min(total_data_points / (self.min_data_points_for_confidence * total_metrics), 1.0)
        
        # Combined confidence score
        confidence = (data_coverage * 0.6) + (data_density * 0.4)
        return min(confidence, 1.0)

    def predict_health_status(self, request: HealthPredictionRequest) -> HealthPredictionResponse:
        """
        Predict health status based on last 24 hours of metrics.
        
        Args:
            request: Health prediction request
            
        Returns:
            Health prediction response with scores and recommendations
        """
        logger.info(f"Starting health prediction for user {request.user_id}")
        
        try:
            # Calculate 24-hour averages
            averages_data = self._calculate_24h_averages(request.user_id)
            
            # Process each metric type
            metric_averages = []
            individual_scores = []
            
            for metric_type, avg_data in averages_data.items():
                is_healthy, health_score = self._calculate_metric_health_score(
                    metric_type, avg_data['average_value']
                )
                
                metric_avg = MetricAverage(
                    metric_type=metric_type.value,
                    average_value=avg_data['average_value'],
                    unit=avg_data['unit'],
                    data_points=avg_data['data_points'],
                    is_healthy=is_healthy,
                    health_score=health_score
                )
                metric_averages.append(metric_avg)
                
                if avg_data['average_value'] is not None:
                    individual_scores.append(health_score)
            
            # Calculate overall health score (weighted average)
            if individual_scores:
                overall_health_score = statistics.mean(individual_scores)
            else:
                overall_health_score = 0.5  # Default neutral score
            
            # Determine health risk level
            if overall_health_score >= self.risk_thresholds[HealthRiskLevel.LOW]:
                health_risk_level = HealthRiskLevel.LOW
            elif overall_health_score >= self.risk_thresholds[HealthRiskLevel.MEDIUM]:
                health_risk_level = HealthRiskLevel.MEDIUM
            else:
                health_risk_level = HealthRiskLevel.HIGH
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(metric_averages)
            
            # Generate risk factors and recommendations
            risk_factors = self._generate_risk_factors(metric_averages)
            recommendations = self._generate_recommendations(metric_averages)
            
            # Prepare raw metrics summary if requested
            raw_metrics_summary = None
            if request.include_metrics:
                raw_metrics_summary = {
                    'total_metrics_analyzed': sum(avg['data_points'] for avg in averages_data.values()),
                    'metrics_by_type': {
                        metric_type.value: avg['data_points'] 
                        for metric_type, avg in averages_data.items()
                    }
                }
            
            response = HealthPredictionResponse(
                user_id=request.user_id,
                prediction_timestamp=datetime.now(timezone.utc),
                overall_health_score=overall_health_score,
                health_risk_level=health_risk_level,
                confidence_score=confidence_score,
                metric_averages=metric_averages,
                risk_factors=risk_factors,
                recommendations=recommendations,
                raw_metrics_summary=raw_metrics_summary,
                model_version=self.model_version,
                prediction_horizon_hours=request.prediction_horizon_hours or 24
            )
            
            logger.info(
                f"Health prediction completed for user {request.user_id}: "
                f"score={overall_health_score:.2f}, risk={health_risk_level.value}, "
                f"confidence={confidence_score:.2f}"
            )
            
            return response
            
        except UserNotFoundException:
            logger.error(f"User not found for health prediction: {request.user_id}")
            raise
        except Exception as e:
            logger.error(f"Health prediction failed for user {request.user_id}: {e}")
            raise

    def get_health_history(self, user_id: str, days: int = 7) -> Dict:
        """
        Get health prediction history for a user.
        
        Args:
            user_id: User ID to get history for
            days: Number of days of history to retrieve
            
        Returns:
            Dictionary with health history data
        """
        # This is a simplified implementation - in production, you'd store predictions
        # and retrieve them from a database
        
        logger.info(f"Getting health history for user {user_id} for {days} days")
        
        # For now, return current prediction as history
        current_prediction = self.predict_health_status(
            HealthPredictionRequest(user_id=user_id)
        )
        
        return {
            'user_id': user_id,
            'current_prediction': current_prediction.dict(),
            'history_available': False,
            'message': 'Health history tracking not yet implemented'
        }