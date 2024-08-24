import logging
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from src.backend.models.models import Vote, UserAnalytics 
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation
import pandas as pd
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.sentiment import SentimentIntensityAnalyzer

# Download necessary NLTK data
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('vader_lexicon')

logger = logging.getLogger(__name__)

class AnalyticsService:
    def get_sentiment_analysis(self, db: Session):
        logger.debug("Entering get_sentiment_analysis method")
        try:
            # Fetch all votes from the database
            votes = db.query(Vote).all()
            
            if not votes:
                logger.info("No votes found in the database")
                return {"error": "No votes found in the database."}

            # Calculate average sentiment score and usefulness rating
            sentiment_scores = [vote.sentiment_score for vote in votes if vote.sentiment_score is not None]
            usefulness_ratings = [vote.usefulness_rating for vote in votes if vote.usefulness_rating is not None]
            
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
            avg_usefulness = sum(usefulness_ratings) / len(usefulness_ratings) if usefulness_ratings else 0

            # Calculate upvote percentage
            total_votes = len(votes)
            upvotes = sum(1 for vote in votes if vote.is_upvote)
            upvote_percentage = (upvotes / total_votes) * 100 if total_votes > 0 else 0

            # Prepare daily data
            daily_data = {}
            for vote in votes:
                date = vote.created_at.date()
                if date not in daily_data:
                    daily_data[date] = {"sentiment_scores": [], "usefulness_ratings": []}
                if vote.sentiment_score is not None:
                    daily_data[date]["sentiment_scores"].append(vote.sentiment_score)
                if vote.usefulness_rating is not None:
                    daily_data[date]["usefulness_ratings"].append(vote.usefulness_rating)

            # Calculate daily averages
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
                "sentiment_score_distribution": Counter(sentiment_scores),
                "usefulness_rating_distribution": Counter(usefulness_ratings)
            }

            logger.debug("Exiting get_sentiment_analysis method")
            return result
        except Exception as e:
            logger.exception("Error in get_sentiment_analysis method")
            return {"error": str(e)}

    def save_user_event(self, db: Session, user_id: int, event_type: str, event_data: dict, duration: float = None):
        logger.debug(f"Saving user event: user_id={user_id}, event_type={event_type}, event_data={event_data}, duration={duration}")
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
            logger.debug("User event saved successfully")
            return True
        except Exception as e:
            logger.exception(f"Error saving user event: {str(e)}")
            db.rollback()
            return False
        
    def analyze_feedback_text(self, db: Session):
        logger.debug("Entering analyze_feedback_text method")
        try:
            # Fetch all votes with feedback text
            votes = db.query(Vote).filter(Vote.feedback_text != '').all()

            if not votes:
                logger.info("No feedback texts found in the database")
                return {"message": "No feedback data available"}

            feedback_texts = [vote.feedback_text for vote in votes if vote.feedback_text]
            usefulness_ratings = [vote.usefulness_rating for vote in votes if vote.usefulness_rating is not None]

            # Preprocessing
            stop_words = set(stopwords.words('english'))
            processed_texts = []
            for text in feedback_texts:
                tokens = word_tokenize(text.lower())
                processed_text = ' '.join([word for word in tokens if word.isalnum() and word not in stop_words])
                processed_texts.append(processed_text)

            # Word Frequency Analysis
            all_words = ' '.join(processed_texts).split()
            word_freq = Counter(all_words).most_common(20)

            # Sentiment Analysis
            sia = SentimentIntensityAnalyzer()
            sentiments = [sia.polarity_scores(text)['compound'] for text in feedback_texts]
            avg_sentiment = sum(sentiments) / len(sentiments)

            # Topic Modeling
            vectorizer = TfidfVectorizer(max_features=1000)
            tfidf_matrix = vectorizer.fit_transform(processed_texts)
            
            lda = LatentDirichletAllocation(n_components=5, random_state=42)
            lda.fit(tfidf_matrix)
            
            feature_names = vectorizer.get_feature_names_out()
            topics = []
            for topic_idx, topic in enumerate(lda.components_):
                top_words = [feature_names[i] for i in topic.argsort()[:-10 - 1:-1]]
                topics.append(f"Topic {topic_idx + 1}: {', '.join(top_words)}")

            # Correlation between sentiment and usefulness
            sentiment_usefulness_corr = pd.DataFrame({'sentiment': sentiments, 'usefulness': usefulness_ratings}).corr().iloc[0, 1]

            # Keyword extraction using TF-IDF scores
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

            logger.debug("Exiting analyze_feedback_text method")
            return result
        except Exception as e:
            logger.exception("Error in analyze_feedback_text method")
            return {'error': str(e)}

    def get_user_events(self, db: Session, user_id: int = None):
        logger.debug(f"Entering get_user_events method with user_id: {user_id}")
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

            logger.debug("Exiting get_user_events method")
            return result
        except Exception as e:
            logger.exception("Error in get_user_events method")
            return {'error': str(e)}

    def get_event_summary(self, db: Session):
        logger.debug("Entering get_event_summary method")
        try:
            events = db.query(UserAnalytics.event_type, func.count(UserAnalytics.id)).group_by(UserAnalytics.event_type).all()
            result = {event[0]: event[1] for event in events}

            logger.debug("Exiting get_event_summary method")
            return result
        except Exception as e:
            logger.exception("Error in get_event_summary method")
            return {'error': str(e)}