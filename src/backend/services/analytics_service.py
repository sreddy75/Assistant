import logging
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from src.backend.models.models import Vote, UserAnalytics, User
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation
import pandas as pd
import numpy as np
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.sentiment import SentimentIntensityAnalyzer

logger = logging.getLogger(__name__)

class AnalyticsService:
    def _replace_nan(self, obj):
        if isinstance(obj, float) and np.isnan(obj):
            return None
        elif isinstance(obj, dict):
            return {k: self._replace_nan(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._replace_nan(v) for v in obj]
        return obj

    def get_user_engagement_metrics(self, db: Session):
        try:
            now = datetime.utcnow()
            daily_active = db.query(func.count(func.distinct(UserAnalytics.user_id))).filter(
                UserAnalytics.timestamp > now - timedelta(days=1)
            ).scalar()
            weekly_active = db.query(func.count(func.distinct(UserAnalytics.user_id))).filter(
                UserAnalytics.timestamp > now - timedelta(weeks=1)
            ).scalar()
            monthly_active = db.query(func.count(func.distinct(UserAnalytics.user_id))).filter(
                UserAnalytics.timestamp > now - timedelta(days=30)
            ).scalar()

            user_growth = db.query(
                func.date_trunc('day', User.created_at).label('date'),
                func.count(User.id).label('new_users')
            ).group_by('date').order_by('date').all()

            retention_data = []
            for i in range(4):
                start_date = now - timedelta(weeks=i+1)
                end_date = now - timedelta(weeks=i)
                new_users = db.query(func.count(User.id)).filter(
                    User.created_at.between(start_date, end_date)
                ).scalar()
                retained_users = db.query(func.count(func.distinct(UserAnalytics.user_id))).filter(
                    UserAnalytics.timestamp > end_date,
                    UserAnalytics.user_id.in_(
                        db.query(User.id).filter(User.created_at.between(start_date, end_date))
                    )
                ).scalar()
                retention_rate = retained_users / new_users if new_users > 0 else 0
                retention_data.append({
                    'cohort': start_date.strftime('%Y-%m-%d'),
                    'retention_rate': retention_rate
                })

            result = {
                'active_users': {
                    'daily': daily_active,
                    'weekly': weekly_active,
                    'monthly': monthly_active
                },
                'user_growth': [{'date': str(ug.date), 'new_users': ug.new_users} for ug in user_growth],
                'user_retention': retention_data
            }
            return self._replace_nan(result)
        except Exception as e:
            logger.error(f"Error in get_user_engagement_metrics: {str(e)}")
            return {'error': str(e)}

    def get_interaction_metrics(self, db: Session):
        try:
            total_queries = db.query(func.count(Vote.id)).scalar()
            recent_queries = db.query(
                func.date_trunc('day', Vote.created_at).label('date'),
                func.count(Vote.id).label('query_count')
            ).group_by('date').order_by('date').limit(30).all()

            avg_response_time = db.query(func.avg(UserAnalytics.duration)).filter(
                UserAnalytics.event_type == 'query_response'
            ).scalar()

            session_durations = db.query(
                UserAnalytics.user_id,
                func.sum(UserAnalytics.duration).label('total_duration')
            ).group_by(UserAnalytics.user_id).all()
            
            avg_session_duration = sum(session.total_duration for session in session_durations) / len(session_durations) if session_durations else 0

            result = {
                'query_volume': {
                    'total': total_queries,
                    'recent_trend': [{'date': str(q.date), 'count': q.query_count} for q in recent_queries]
                },
                'avg_response_time': float(avg_response_time) if avg_response_time else None,
                'avg_session_duration': float(avg_session_duration) if avg_session_duration is not None else None
            }
            return self._replace_nan(result)
        except Exception as e:
            logger.error(f"Error in get_interaction_metrics: {str(e)}")
            return {'error': str(e)}

    def get_quality_metrics(self, db: Session):
        try:
            votes = db.query(Vote).all()
            upvotes = sum(1 for vote in votes if vote.is_upvote)
            total_votes = len(votes)
            satisfaction_score = (upvotes / total_votes) * 100 if total_votes > 0 else 0

            positive_feedback = db.query(Vote.feedback_text).filter(Vote.sentiment_score > 0).all()
            word_freq = Counter(' '.join([fb.feedback_text for fb in positive_feedback]).split()).most_common(50)

            sentiment_trend = db.query(
                func.date_trunc('day', Vote.created_at).label('date'),
                func.avg(Vote.sentiment_score).label('avg_sentiment')
            ).group_by('date').order_by('date').all()

            result = {
                'satisfaction_score': satisfaction_score,
                'word_cloud_data': dict(word_freq),
                'sentiment_trend': [{'date': str(st.date), 'sentiment': st.avg_sentiment} for st in sentiment_trend]
            }
            return self._replace_nan(result)
        except Exception as e:
            logger.error(f"Error in get_quality_metrics: {str(e)}")
            return {'error': str(e)}

    def get_usage_patterns(self, db: Session):
        try:
            popular_topics = db.query(
                Vote.query.label('topic'),
                func.count(Vote.id).label('count')
            ).group_by(Vote.query).order_by(func.count(Vote.id).desc()).limit(10).all()

            peak_usage = db.query(
                extract('hour', UserAnalytics.timestamp).label('hour'),
                func.count(UserAnalytics.id).label('count')
            ).group_by('hour').order_by('hour').all()

            feature_adoption = db.query(
                UserAnalytics.event_type,
                func.count(UserAnalytics.id).label('count')
            ).group_by(UserAnalytics.event_type).all()

            result = {
                'popular_topics': [{'topic': pt.topic, 'count': pt.count} for pt in popular_topics],
                'peak_usage': [{'hour': pu.hour, 'count': pu.count} for pu in peak_usage],
                'feature_adoption': [{'feature': fa.event_type, 'count': fa.count} for fa in feature_adoption]
            }
            return self._replace_nan(result)
        except Exception as e:
            logger.error(f"Error in get_usage_patterns: {str(e)}")
            return {'error': str(e)}

    def get_sentiment_analysis(self, db: Session):
        try:
            votes = db.query(Vote).all()
            
            if not votes:
                return {"message": "No votes found in the database."}

            sentiment_scores = [vote.sentiment_score for vote in votes if vote.sentiment_score is not None]
            usefulness_ratings = [vote.usefulness_rating for vote in votes if vote.usefulness_rating is not None]
            
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
            avg_usefulness = sum(usefulness_ratings) / len(usefulness_ratings) if usefulness_ratings else 0

            total_votes = len(votes)
            upvotes = sum(1 for vote in votes if vote.is_upvote)
            upvote_percentage = (upvotes / total_votes) * 100 if total_votes > 0 else 0

            daily_data = {}
            for vote in votes:
                date = vote.created_at.date().isoformat()
                if date not in daily_data:
                    daily_data[date] = {"sentiment_scores": [], "usefulness_ratings": []}
                if vote.sentiment_score is not None:
                    daily_data[date]["sentiment_scores"].append(vote.sentiment_score)
                if vote.usefulness_rating is not None:
                    daily_data[date]["usefulness_ratings"].append(vote.usefulness_rating)

            daily_averages = {
                date: {
                    "sentiment_score": sum(data["sentiment_scores"]) / len(data["sentiment_scores"]) if data["sentiment_scores"] else None,
                    "usefulness_rating": sum(data["usefulness_ratings"]) / len(data["usefulness_ratings"]) if data["usefulness_ratings"] else None
                }
                for date, data in daily_data.items()
            }

            result = {
                "average_sentiment_score": avg_sentiment,
                "average_usefulness_rating": avg_usefulness,
                "upvote_percentage": upvote_percentage,
                "daily_data": daily_averages,
                "sentiment_score_distribution": dict(Counter(sentiment_scores)),
                "usefulness_rating_distribution": dict(Counter(usefulness_ratings))
            }
            return self._replace_nan(result)
        except Exception as e:
            logger.error(f"Error in get_sentiment_analysis: {str(e)}")
            return {"error": str(e)}

    def analyze_feedback_text(self, db: Session):
        try:
            votes = db.query(Vote).filter(Vote.feedback_text != '').all()

            if not votes:
                return {"message": "No feedback data available"}

            feedback_texts = [vote.feedback_text for vote in votes if vote.feedback_text]
            usefulness_ratings = [vote.usefulness_rating for vote in votes if vote.usefulness_rating is not None]

            stop_words = set(stopwords.words('english'))
            processed_texts = []
            for text in feedback_texts:
                tokens = word_tokenize(text.lower())
                processed_text = ' '.join([word for word in tokens if word.isalnum() and word not in stop_words])
                processed_texts.append(processed_text)

            all_words = ' '.join(processed_texts).split()
            word_freq = Counter(all_words).most_common(20)

            sia = SentimentIntensityAnalyzer()
            sentiments = [sia.polarity_scores(text)['compound'] for text in feedback_texts]
            avg_sentiment = sum(sentiments) / len(sentiments)

            vectorizer = TfidfVectorizer(max_features=1000)
            tfidf_matrix = vectorizer.fit_transform(processed_texts)
            
            lda = LatentDirichletAllocation(n_components=5, random_state=42)
            lda.fit(tfidf_matrix)
            
            feature_names = vectorizer.get_feature_names_out()
            topics = []
            for topic_idx, topic in enumerate(lda.components_):
                top_words = [feature_names[i] for i in topic.argsort()[:-10 - 1:-1]]
                topics.append(f"Topic {topic_idx + 1}: {', '.join(top_words)}")

            sentiment_usefulness_corr = pd.DataFrame({'sentiment': sentiments, 'usefulness': usefulness_ratings}).corr().iloc[0, 1]

            tfidf_scores = tfidf_matrix.sum(axis=0).A1
            tfidf_dict = dict(zip(feature_names, tfidf_scores))
            top_keywords = sorted(tfidf_dict.items(), key=lambda x: x[1], reverse=True)[:20]

            result = {
                'word_frequency': dict(word_freq),
                'average_sentiment': avg_sentiment,
                'sentiment_distribution': {
                    'positive': sum(1 for s in sentiments if s > 0.05) / len(sentiments),
                    'neutral': sum(1 for s in sentiments if -0.05 <= s <= 0.05) / len(sentiments),
                    'negative': sum(1 for s in sentiments if s < -0.05) / len(sentiments)
                },
                'topics': topics,
                'sentiment_usefulness_correlation': sentiment_usefulness_corr,
                'top_keywords': dict(top_keywords),
                'feedback_count': len(feedback_texts)
            }
            return self._replace_nan(result)
        except Exception as e:
            logger.error(f"Error in analyze_feedback_text: {str(e)}")
            return {'error': str(e)}

    def save_user_event(self, db: Session, user_id: int, event_type: str, event_data: dict, duration: float = None):
        try:
            new_event = UserAnalytics(
                user_id=user_id,                
                event_type=event_type,
                event_data=event_data,
                duration=duration,
                timestamp=datetime.utcnow()
            )
            db.add(new_event)
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving user event: {str(e)}")
            db.rollback()
            return False

    def get_user_events(self, db: Session, user_id: int = None):
        try:
            query = db.query(UserAnalytics)
            if user_id:
                query = query.filter_by(user_id=user_id)            
            events = query.order_by(UserAnalytics.timestamp.desc()).all()
            
            result = [
                {
                    "user_id": event.user_id,                    
                    "event_type": event.event_type,
                    "event_data": event.event_data,
                    "timestamp": event.timestamp,
                    "duration": event.duration
                }
                for event in events
            ]
            return self._replace_nan(result)
        except Exception as e:
            logger.error(f"Error in get_user_events: {str(e)}")
            return {'error': str(e)}

    def get_event_summary(self, db: Session):
        try:
            events = db.query(UserAnalytics.event_type, func.count(UserAnalytics.id)).group_by(UserAnalytics.event_type).all()
            result = {event[0]: event[1] for event in events}
            return self._replace_nan(result)
        except Exception as e:
            logger.error(f"Error in get_event_summary: {str(e)}")
            return {'error': str(e)}

    def get_user_retention(self, db: Session):
        try:
            now = datetime.utcnow()
            retention_data = []
            for i in range(4):  # Calculate retention for the last 4 weeks
                start_date = now - timedelta(weeks=i+1)
                end_date = now - timedelta(weeks=i)
                
                new_users = db.query(func.count(User.id)).filter(
                    User.created_at.between(start_date, end_date)
                ).scalar()
                
                retained_users = db.query(func.count(func.distinct(UserAnalytics.user_id))).filter(
                    UserAnalytics.timestamp > end_date,
                    UserAnalytics.user_id.in_(
                        db.query(User.id).filter(User.created_at.between(start_date, end_date))
                    )
                ).scalar()
                
                retention_rate = (retained_users / new_users) * 100 if new_users > 0 else 0
                retention_data.append({
                    'cohort': start_date.strftime('%Y-%m-%d'),
                    'retention_rate': retention_rate
                })
            
            return self._replace_nan(retention_data)
        except Exception as e:
            logger.error(f"Error in get_user_retention: {str(e)}")
            return {'error': str(e)}

    def get_user_segmentation(self, db: Session):
        try:
            now = datetime.utcnow()
            one_month_ago = now - timedelta(days=30)
            
            # Segment users based on activity in the last 30 days
            active_users = db.query(func.count(func.distinct(UserAnalytics.user_id))).filter(
                UserAnalytics.timestamp > one_month_ago
            ).scalar()
            
            total_users = db.query(func.count(User.id)).scalar()
            inactive_users = total_users - active_users
            
            # Segment users based on engagement level
            high_engagement = db.query(func.count(func.distinct(UserAnalytics.user_id))).filter(
                UserAnalytics.timestamp > one_month_ago
            ).group_by(UserAnalytics.user_id).having(func.count(UserAnalytics.id) > 10).count()
            
            medium_engagement = db.query(func.count(func.distinct(UserAnalytics.user_id))).filter(
                UserAnalytics.timestamp > one_month_ago
            ).group_by(UserAnalytics.user_id).having(func.count(UserAnalytics.id).between(5, 10)).count()
            
            low_engagement = active_users - high_engagement - medium_engagement
            
            result = {
                'total_users': total_users,
                'active_users': active_users,
                'inactive_users': inactive_users,
                'high_engagement': high_engagement,
                'medium_engagement': medium_engagement,
                'low_engagement': low_engagement
            }
            
            return self._replace_nan(result)
        except Exception as e:
            logger.error(f"Error in get_user_segmentation: {str(e)}")
            return {'error': str(e)}

    def get_feature_usage(self, db: Session):
        try:
            feature_usage = db.query(
                UserAnalytics.event_type,
                func.count(UserAnalytics.id).label('usage_count')
            ).group_by(UserAnalytics.event_type).order_by(func.count(UserAnalytics.id).desc()).all()
            
            result = [{'feature': event.event_type, 'usage_count': event.usage_count} for event in feature_usage]
            return self._replace_nan(result)
        except Exception as e:
            logger.error(f"Error in get_feature_usage: {str(e)}")
            return {'error': str(e)}

    def get_user_journey(self, db: Session, user_id: int):
        try:
            user_events = db.query(UserAnalytics).filter(
                UserAnalytics.user_id == user_id
            ).order_by(UserAnalytics.timestamp).all()
            
            journey = [
                {
                    'event_type': event.event_type,
                    'timestamp': event.timestamp.isoformat(),
                    'event_data': event.event_data
                }
                for event in user_events
            ]
            
            return self._replace_nan(journey)
        except Exception as e:
            logger.error(f"Error in get_user_journey: {str(e)}")
            return {'error': str(e)}

    def get_conversion_funnel(self, db: Session):
        try:
            now = datetime.utcnow()
            one_month_ago = now - timedelta(days=30)
            
            total_visitors = db.query(func.count(func.distinct(UserAnalytics.user_id))).filter(
                UserAnalytics.timestamp > one_month_ago
            ).scalar()
            
            signed_up = db.query(func.count(User.id)).filter(
                User.created_at > one_month_ago
            ).scalar()
            
            active_users = db.query(func.count(func.distinct(UserAnalytics.user_id))).filter(
                UserAnalytics.timestamp > one_month_ago,
                UserAnalytics.event_type.in_(['query', 'feedback'])
            ).scalar()
            
            paying_users = db.query(func.count(func.distinct(UserAnalytics.user_id))).filter(
                UserAnalytics.timestamp > one_month_ago,
                UserAnalytics.event_type == 'subscription'
            ).scalar()
            
            result = {
                'total_visitors': total_visitors,
                'signed_up': signed_up,
                'active_users': active_users,
                'paying_users': paying_users
            }
            
            return self._replace_nan(result)
        except Exception as e:
            logger.error(f"Error in get_conversion_funnel: {str(e)}")
            return {'error': str(e)}

    def get_churn_rate(self, db: Session):
        try:
            now = datetime.utcnow()
            one_month_ago = now - timedelta(days=30)
            two_months_ago = now - timedelta(days=60)
            
            users_month_ago = db.query(func.count(User.id)).filter(
                User.created_at <= one_month_ago
            ).scalar()
            
            active_users = db.query(func.count(func.distinct(UserAnalytics.user_id))).filter(
                UserAnalytics.timestamp > one_month_ago,
                UserAnalytics.user_id.in_(
                    db.query(User.id).filter(User.created_at <= one_month_ago)
                )
            ).scalar()
            
            churned_users = users_month_ago - active_users
            churn_rate = (churned_users / users_month_ago) * 100 if users_month_ago > 0 else 0
            
            result = {
                'total_users_month_ago': users_month_ago,
                'active_users': active_users,
                'churned_users': churned_users,
                'churn_rate': churn_rate
            }
            
            return self._replace_nan(result)
        except Exception as e:
            logger.error(f"Error in get_churn_rate: {str(e)}")
            return {'error': str(e)}