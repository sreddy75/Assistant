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
from src.backend.kr8.vectordb.pgvector.pgvector2 import PgVector2
from sqlalchemy import func
from typing import Dict
import pandas as pd


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

def find_similar_queries(query: str, rated_queries: Tuple[str, ...], top_n: int = 5) -> List[int]:
    vectorizer = TfidfVectorizer()
    # Convert rated_queries tuple to a list before concatenation
    all_queries = [query] + list(rated_queries)
    tfidf_matrix = vectorizer.fit_transform(all_queries)
    cosine_similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
    similar_indices = cosine_similarities.argsort()[:-top_n-1:-1]
    return similar_indices.tolist()

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
    
from typing import Dict, List
from sqlalchemy import MetaData, Table, select, func
from sqlalchemy.orm import sessionmaker
from collections import Counter
import pandas as pd
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.sentiment import SentimentIntensityAnalyzer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation

# Download necessary NLTK data
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('vader_lexicon')

def analyze_feedback_text() -> Dict:
    metadata = MetaData()
    votes_table = Table('votes', metadata, autoload_with=engine)

    with SessionLocal() as session:
        try:
            query = select(votes_table.c.feedback_text, votes_table.c.usefulness_rating).where(votes_table.c.feedback_text != '')
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
            import traceback
            traceback.print_exc()
            return {'error': str(e)}

def adjust_response_based_on_feedback(base_response: str, query: str, db: Session) -> str:
    highly_rated = get_highly_rated_responses(db)
    if not highly_rated:
        return base_response

    rated_queries, rated_responses = zip(*highly_rated)
    
    # Convert rated_queries to a list
    rated_queries_list = list(rated_queries)
    
    similar_indices = find_similar_queries(query, rated_queries_list)
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