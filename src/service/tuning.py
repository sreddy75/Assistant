import traceback
from sqlalchemy.orm import Session
from sqlalchemy import Integer, func
from typing import Any, List, Tuple, Dict
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from backend.backend import Vote
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Tuple
from sqlalchemy import create_engine, Table, MetaData, select
from sqlalchemy.orm import sessionmaker
import pandas as pd
import os
from sqlalchemy.orm import Session
from sqlalchemy import func, Integer
from typing import List, Tuple
import random
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from config.client_config import is_feedback_sentiment_analysis_enabled
from kr8.vectordb.pgvector.pgvector2 import PgVector2

# Assuming you have these environment variables set
DB_URL = os.getenv("DB_URL", "postgresql+psycopg://ai:ai@pgvector:5432/ai")

engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_highly_rated_responses(db: Session, threshold: float = 0.7) -> List[Tuple[str, str]]:
    """
    Fetch queries and responses with a high percentage of upvotes or high usefulness ratings,
    depending on whether the advanced feedback feature is enabled.
    """
    if is_feedback_sentiment_analysis_enabled():
        # For advanced feedback, use usefulness rating
        subquery = (
            db.query(
                Vote.query,
                Vote.response,
                func.avg(Vote.usefulness_rating).label("avg_usefulness")
            )
            .group_by(Vote.query, Vote.response)
            .subquery()
        )
        
        results = db.query(subquery).filter(subquery.c.avg_usefulness >= 4).all()
    else:
        # For simple feedback, use upvote percentage
        subquery = (
            db.query(
                Vote.query,
                Vote.response,
                func.sum(Vote.is_upvote.cast(Integer)).label("upvotes"),
                func.count(Vote.id).label("total_votes")
            )
            .group_by(Vote.query, Vote.response)
            .subquery()
        )
        
        results = db.query(subquery).filter(subquery.c.upvotes / subquery.c.total_votes >= threshold).all()

    return [(r.query, r.response) for r in results]

def find_similar_queries(query: str, rated_queries: List[str], top_n: int = 5) -> List[int]:
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([query] + rated_queries)
    cosine_similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
    similar_indices = cosine_similarities.argsort()[:-top_n-1:-1]
    return similar_indices.tolist()

from sqlalchemy import func
from typing import Dict
import pandas as pd

def get_sentiment_analysis() -> Dict[str, Any]:
    metadata = MetaData()
    votes_table = Table('votes', metadata, autoload_with=engine)

    with SessionLocal() as session:
        try:
            print("Querying votes table...")
            query = select(votes_table)
            result = session.execute(query)
            votes = result.fetchall()

            print(f"Number of votes: {len(votes)}")
            if not votes:
                print("No votes found in the database.")
                return {"error": "No votes found in the database."}

            print("Creating DataFrame...")
            df = pd.DataFrame([{c.name: getattr(vote, c.name) for c in votes_table.columns} for vote in votes])
            
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
                        
def plot_sentiment_analysis(analysis: Dict):
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

def get_vote_analysis(vector_db: PgVector2) -> Dict:
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
    
def analyze_feedback_text() -> Dict:
    metadata = MetaData()
    votes_table = Table('votes', metadata, autoload_with=engine)

    with SessionLocal() as session:
        try:
            query = select(votes_table.c.feedback_text).where(votes_table.c.feedback_text != '')
            result = session.execute(query)
            feedbacks = result.fetchall()

            feedback_text = ' '.join([f[0] for f in feedbacks if f[0] is not None])
            
            # Here you could implement more sophisticated text analysis,
            # such as topic modeling or keyword extraction
            # For this example, we'll just return word frequency
            words = feedback_text.split()
            word_freq = pd.Series(words).value_counts().head(20).to_dict()
            
            return {'word_frequency': word_freq}

        except Exception as e:
            print(f"Error analyzing feedback text: {e}")
            import traceback
            traceback.print_exc()
            return {'word_frequency': {}}

def adjust_response_based_on_feedback(base_response: str, query: str, db: Session) -> str:
    highly_rated = get_highly_rated_responses(db)
    if not highly_rated:
        return base_response

    rated_queries, rated_responses = zip(*highly_rated)
    
    similar_indices = find_similar_queries(query, rated_queries)
    similar_responses = [rated_responses[i] for i in similar_indices]
    
    if is_feedback_sentiment_analysis_enabled():
        # Use sentiment and usefulness to weight the responses
        weights = []
        for i in similar_indices:
            vote = db.query(Vote).filter(Vote.query == rated_queries[i], Vote.response == rated_responses[i]).first()
            if vote:
                weight = (vote.sentiment_score + 1) * vote.usefulness_rating  # Combine sentiment and usefulness
                weights.append(weight)
            else:
                weights.append(1)  # Default weight if no vote found
    else:
        # Use simple upvotes as weights
        weights = []
        for i in similar_indices:
            vote = db.query(Vote).filter(Vote.query == rated_queries[i], Vote.response == rated_responses[i]).first()
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