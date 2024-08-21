from datetime import datetime
from sqlalchemy import create_engine, Table, Column, Integer, String, TIMESTAMP, JSON, Float, func, select, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Any, List, Tuple, Dict
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import traceback
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import LatentDirichletAllocation
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.sentiment import SentimentIntensityAnalyzer
from collections import Counter
import random

from config.client_config import is_feedback_sentiment_analysis_enabled
from src.backend.kr8.vectordb.pgvector.pgvector2 import PgVector2
from backend.models.models import Vote

# Download necessary NLTK data
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('vader_lexicon')

Base = declarative_base()

class UserAnalytics(Base):
    __tablename__ = 'user_analytics'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    event_type = Column(String(50))
    event_data = Column(JSON)
    timestamp = Column(TIMESTAMP, default=datetime.utcnow)
    duration = Column(Float)  # For tracking conversation duration

class AnalyticsService:
    def __init__(self, db_url):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.metadata = MetaData()
        self.votes_table = Table('votes', self.metadata, autoload_with=self.engine)

    def log_event(self, user_id, event_type, event_data, duration=None):
        session = self.Session()
        try:
            analytics_event = UserAnalytics(
                user_id=user_id,
                event_type=event_type,
                event_data=event_data,
                duration=duration
            )
            session.add(analytics_event)
            session.commit()
        except Exception as e:
            print(f"Error logging event: {e}")
        finally:
            session.close()

    def get_most_used_tools(self):
        session = self.Session()
        try:
            events = session.query(UserAnalytics).filter(UserAnalytics.event_type == 'assistant_response').all()
            tool_usage = {}
            for event in events:
                tools = event.event_data.get('tools_used', [])
                for tool in tools:
                    tool_usage[tool] = tool_usage.get(tool, 0) + 1
            return sorted(tool_usage.items(), key=lambda x: x[1], reverse=True)
        finally:
            session.close()

    def get_user_events(self, user_id=None):
        session = self.Session()
        try:
            query = session.query(UserAnalytics)
            if user_id:
                query = query.filter_by(user_id=user_id)
            events = query.order_by(UserAnalytics.timestamp.desc()).all()
            return [
                {
                    "user_id": event.user_id,
                    "event_type": event.event_type,
                    "event_data": event.event_data,
                    "timestamp": event.timestamp,
                    "duration": event.duration
                }
                for event in events
            ]
        finally:
            session.close()

    def get_unique_users(self):
        session = self.Session()
        try:
            return session.query(UserAnalytics.user_id).distinct().count()
        finally:
            session.close()

    def get_event_summary(self):
        session = self.Session()
        try:
            events = session.query(UserAnalytics.event_type, UserAnalytics.id).all()
            return {event[0]: len(list(filter(lambda x: x[0] == event[0], events))) for event in set(events)}
        finally:
            session.close()

    def get_sentiment_analysis(self) -> Dict[str, Any]:
        session = self.Session()
        try:
            print("Querying votes table...")
            query = select(self.votes_table)
            result = session.execute(query)
            votes = result.fetchall()

            print(f"Number of votes: {len(votes)}")
            if not votes:
                print("No votes found in the database.")
                return {"error": "No votes found in the database."}

            print("Creating DataFrame...")
            df = pd.DataFrame([{c.name: getattr(vote, c.name) for c in self.votes_table.columns} for vote in votes])
            
            print("DataFrame info:")
            print(df.info())

            result = {}
            
            numeric_columns = df.select_dtypes(include=['number']).columns
            
            for col in numeric_columns:
                if col in ['sentiment_score', 'usefulness_rating']:
                    result[f'average_{col}'] = df[col].mean()
                    result[f'{col}_distribution'] = df[col].value_counts().to_dict()
            
            if 'is_upvote' in df.columns:
                result['upvote_percentage'] = (df['is_upvote'].sum() / len(df)) * 100
            
            if 'created_at' in df.columns:
                df['date'] = pd.to_datetime(df['created_at'])
                daily_data = df.set_index('date')[numeric_columns].resample('D').mean()
                result['daily_data'] = {col: daily_data[col].to_dict() for col in daily_data.columns}
            
            print("Analysis result:", result)
            return result

        except Exception as e:
            print(f"Error processing votes: {str(e)}")
            traceback.print_exc()
            return {"error": f"An error occurred while processing votes: {str(e)}"}
        finally:
            session.close()

    def plot_sentiment_analysis(self, analysis: Dict):
        fig, axes = plt.subplots(2, 2, figsize=(15, 15))
        
        if "error" in analysis:
            for ax in axes.flat:
                ax.text(0.5, 0.5, "No data available", ha='center', va='center')
                ax.axis('off')
        else:
            # Plot daily sentiment if available
            if 'daily_data' in analysis and 'sentiment_score' in analysis['daily_data']:
                daily_sentiment = pd.DataFrame(analysis['daily_data']['sentiment_score'], columns=['sentiment_score'])
                
                # Convert to numeric and drop any non-numeric values
                daily_sentiment['sentiment_score'] = pd.to_numeric(daily_sentiment['sentiment_score'], errors='coerce')
                daily_sentiment = daily_sentiment.dropna()
                
                if not daily_sentiment.empty:
                    daily_sentiment.plot(ax=axes[0, 0])
                    axes[0, 0].set_title('Daily Average Sentiment')
                    axes[0, 0].set_ylabel('Sentiment Score')
                else:
                    axes[0, 0].text(0.5, 0.5, "No valid sentiment data available", ha='center', va='center')
                    axes[0, 0].axis('off')
            else:
                axes[0, 0].text(0.5, 0.5, "Daily Sentiment Data Not Available", ha='center', va='center')
                axes[0, 0].axis('off')
            
            # Plot usefulness distribution if available
            if 'usefulness_rating_distribution' in analysis:
                usefulness = pd.DataFrame.from_dict(analysis['usefulness_rating_distribution'], orient='index', columns=['count'])
                sns.barplot(x=usefulness.index, y='count', data=usefulness, ax=axes[0, 1])
                axes[0, 1].set_title('Distribution of Usefulness Ratings')
                axes[0, 1].set_xlabel('Usefulness Rating')
                axes[0, 1].set_ylabel('Count')
            else:
                axes[0, 1].text(0.5, 0.5, "Usefulness Data Not Available", ha='center', va='center')
                axes[0, 1].axis('off')
            
            # Plot upvote percentage if available
            if 'upvote_percentage' in analysis:
                axes[1, 0].bar(['Upvotes', 'Downvotes'], [analysis['upvote_percentage'], 100 - analysis['upvote_percentage']])
                axes[1, 0].set_title('Upvote vs Downvote Percentage')
                axes[1, 0].set_ylabel('Percentage')
            else:
                axes[1, 0].text(0.5, 0.5, "Upvote Data Not Available", ha='center', va='center')
                axes[1, 0].axis('off')
            
            # Plot sentiment score distribution if available
            if 'sentiment_score_distribution' in analysis:
                sentiment = pd.DataFrame.from_dict(analysis['sentiment_score_distribution'], orient='index', columns=['count'])
                sns.barplot(x=sentiment.index, y='count', data=sentiment, ax=axes[1, 1])
                axes[1, 1].set_title('Distribution of Sentiment Scores')
                axes[1, 1].set_xlabel('Sentiment Score')
                axes[1, 1].set_ylabel('Count')
            else:
                axes[1, 1].text(0.5, 0.5, "Sentiment Score Distribution Not Available", ha='center', va='center')
                axes[1, 1].axis('off')
        
        plt.tight_layout()
        return fig

    def get_vote_analysis(self, vector_db: PgVector2) -> Dict:
        with vector_db.Session() as sess:
            total_votes = sess.query(vector_db.table).count()
            upvotes = sess.query(vector_db.table).filter(vector_db.table.c.is_upvote == True).count()
            
            if total_votes > 0:
                upvote_percentage = (upvotes / total_votes) * 100
            else:
                upvote_percentage = 0

            vote_distribution = {
                "Upvotes": upvotes,
                "Downvotes": total_votes - upvotes
            }

            return {
                "total_votes": total_votes,
                "upvote_percentage": upvote_percentage,
                "vote_distribution": vote_distribution
            }

    def analyze_feedback_text(self) -> Dict:
        session = self.Session()
        try:
            query = select(self.votes_table.c.feedback_text, self.votes_table.c.usefulness_rating).where(self.votes_table.c.feedback_text != '')
            result = session.execute(query)
            feedbacks = result.fetchall()

            feedback_texts = [f[0] for f in feedbacks if f[0] is not None]
            usefulness_ratings = [f[1] for f in feedbacks if f[1] is not None]

            if not feedback_texts:
                return {"message": "No feedback data available"}

            # 1. Preprocessing
            stop_words = set(stopwords.words('english'))
            processed_texts = []
            for text in feedback_texts:
                tokens = word_tokenize(text.lower())
                processed_text = ' '.join([word for word in tokens if word.isalnum() and word not in stop_words])
                processed_texts.append(processed_text)

            # 2. Word Frequency Analysis
            all_words = ' '.join(processed_texts).split()
            word_freq = Counter(all_words).most_common(20)

            # 3. Sentiment Analysis
            sia = SentimentIntensityAnalyzer()
            sentiments = [sia.polarity_scores(text)['compound'] for text in feedback_texts]
            avg_sentiment = sum(sentiments) / len(sentiments)

            # 4. Topic Modeling
            vectorizer = TfidfVectorizer(max_features=1000)
            tfidf_matrix = vectorizer.fit_transform(processed_texts)
            
            lda = LatentDirichletAllocation(n_components=5, random_state=42)
            lda.fit(tfidf_matrix)
            
            feature_names = vectorizer.get_feature_names_out()
            topics = []
            for topic_idx, topic in enumerate(lda.components_):
                top_words = [feature_names[i] for i in topic.argsort()[:-10 - 1:-1]]
                topics.append(f"Topic {topic_idx + 1}: {', '.join(top_words)}")

            # 5. Correlation between sentiment and usefulness
            sentiment_usefulness_corr = pd.DataFrame({'sentiment': sentiments, 'usefulness': usefulness_ratings}).corr().iloc[0, 1]

            # 6. Keyword extraction using TF-IDF scores
            tfidf_scores = tfidf_matrix.sum(axis=0).A1
            tfidf_dict = dict(zip(feature_names, tfidf_scores))
            top_keywords = sorted(tfidf_dict.items(), key=lambda x: x[1], reverse=True)[:20]

            return {
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

        except Exception as e:
            print(f"Error analyzing feedback text: {e}")
            traceback.print_exc()
            return {'error': str(e)}
        finally:
            session.close()

    def get_highly_rated_responses(self, threshold: float = 0.7) -> List[Tuple[str, str]]:
        session = self.Session()
        try:
            if is_feedback_sentiment_analysis_enabled():
                # For advanced feedback, use usefulness rating
                subquery = (
                    session.query(
                        Vote.query,
                        Vote.response,
                        func.avg(Vote.usefulness_rating).label("avg_usefulness")
                    )
                    .group_by(Vote.query, Vote.response)
                    .subquery()
                )
                
                results = session.query(subquery).filter(subquery.c.avg_usefulness >= 4).all()
            else:
                # For simple feedback, use upvote percentage
                subquery = (
                    session.query(
                        Vote.query,
                        Vote.response,
                        func.sum(Vote.is_upvote.cast(Integer)).label("upvotes"),
                        func.count(Vote.id).label("total_votes")
                    )
                    .group_by(Vote.query, Vote.response)
                    .subquery()
                )
                
                results = session.query(subquery).filter(subquery.c.upvotes / subquery.c.total_votes >= threshold).all()

            return [(r.query, r.response) for r in results]
        finally:
            session.close()

    def find_similar_queries(self, query: str, rated_queries: Tuple[str, ...], top_n: int = 5) -> List[int]:
        vectorizer = TfidfVectorizer()
        all_queries = [query] + list(rated_queries)
        tfidf_matrix = vectorizer.fit_transform(all_queries)
        cosine_similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
        similar_indices = cosine_similarities.argsort()[:-top_n-1:-1]
        return similar_indices.tolist()

    def adjust_response_based_on_feedback(self, base_response: str, query: str) -> str:
        session = self.Session()
        try:
            highly_rated = self.get_highly_rated_responses()
            if not highly_rated:
                return base_response

            rated_queries, rated_responses = zip(*highly_rated)
            
            rated_queries_list = list(rated_queries)
            
            similar_indices = self.find_similar_queries(query, rated_queries_list)
            similar_responses = [rated_responses[i] for i in similar_indices]
                
            if is_feedback_sentiment_analysis_enabled():
                # Use sentiment and usefulness to weight the responses
                weights = []
                for i in similar_indices:
                    vote = session.query(Vote).filter(Vote.query == rated_queries[i], Vote.response == rated_responses[i]).first()
                    if vote:
                        weight = (vote.sentiment_score + 1) * vote.usefulness_rating  # Combine sentiment and usefulness
                        weights.append(weight)
                    else:
                        weights.append(1)  # Default weight if no vote found
            else:
                # Use simple upvotes as weights
                weights = []
                for i in similar_indices:
                    vote = session.query(Vote).filter(Vote.query == rated_queries[i], Vote.response == rated_responses[i]).first()
                    if vote:
                        weight = 2 if vote.is_upvote else 1  # Simple weighting: upvotes count double
                        weights.append(weight)
                    else:
                        weights.append(1)  # Default weight if no vote found
            
            # Normalize weights
            total_weight = sum(weights)
            if total_weight == 0:
                return base_response
            weights = [w / total_weight for w in weights]
            
            # Weighted random choice of response
            chosen_response = random.choices(similar_responses, weights=weights)[0]
            
            return chosen_response
        finally:
            session.close()

# Initialize the AnalyticsService
analytics_service = AnalyticsService(os.getenv("DB_URL"))