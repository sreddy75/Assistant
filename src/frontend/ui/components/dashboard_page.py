import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from ui.components.utils import BACKEND_URL

def fetch_data(endpoint):
    try:
        response = requests.get(f"{BACKEND_URL}{endpoint}")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"Failed to fetch data from {endpoint}: {str(e)}")
        return None

def render_dashboard_analytics():    

    # Fetch data from all relevant endpoints
    sentiment_analysis = fetch_data("/api/v1/analytics/sentiment-analysis")
    feedback_analysis = fetch_data("/api/v1/analytics/feedback-analysis")
    user_events = fetch_data("/api/v1/analytics/user-events")
    event_summary = fetch_data("/api/v1/analytics/event-summary")

    if all(data is None for data in [sentiment_analysis, feedback_analysis, user_events, event_summary]):
        st.warning("Failed to fetch data from the API. Please check the server connection.")
        return

    # Sentiment Analysis Section
    st.subheader("Sentiment Analysis")
    if sentiment_analysis is None:
        st.warning("No sentiment analysis data available.")
    else:
        display_sentiment_analysis(sentiment_analysis)            

def display_sentiment_analysis(data):
    col1, col2, col3 = st.columns(3)
    with col1:
        if 'average_sentiment_score' in data:
            st.metric("Average Sentiment Score", f"{data['average_sentiment_score']:.2f}")
    with col2:
        if 'average_usefulness_rating' in data:
            st.metric("Average Usefulness Rating", f"{data['average_usefulness_rating']:.2f}")
    with col3:
        if 'upvote_percentage' in data:
            st.metric("Upvote Percentage", f"{data['upvote_percentage']:.2f}%")

    plot_sentiment_analysis(data)

def plot_sentiment_analysis(analysis):
    if not isinstance(analysis, dict) or len(analysis) == 0:
        st.info("No sentiment analysis data available for plotting")
        return

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Daily Average Sentiment", "Distribution of Usefulness Ratings",
                        "Upvote vs Downvote Percentage", "Distribution of Sentiment Scores")
    )

    if 'daily_data' in analysis:
        daily_sentiment = pd.DataFrame.from_dict(analysis['daily_data'], orient='index')
        daily_sentiment.index = pd.to_datetime(daily_sentiment.index)
        fig.add_trace(go.Scatter(x=daily_sentiment.index, y=daily_sentiment['sentiment_score'], mode='lines', name='Sentiment Score'), row=1, col=1)
        fig.add_trace(go.Scatter(x=daily_sentiment.index, y=daily_sentiment['usefulness_rating'], mode='lines', name='Usefulness Rating'), row=1, col=1)

    if 'usefulness_rating_distribution' in analysis:
        usefulness = pd.DataFrame.from_dict(analysis['usefulness_rating_distribution'], orient='index', columns=['count'])
        fig.add_trace(go.Bar(x=usefulness.index, y=usefulness['count']), row=1, col=2)

    if 'upvote_percentage' in analysis:
        fig.add_trace(go.Bar(x=['Upvotes', 'Downvotes'], y=[analysis['upvote_percentage'], 100 - analysis['upvote_percentage']]), row=2, col=1)

    if 'sentiment_score_distribution' in analysis:
        sentiment = pd.DataFrame.from_dict(analysis['sentiment_score_distribution'], orient='index', columns=['count'])
        fig.add_trace(go.Bar(x=sentiment.index, y=sentiment['count']), row=2, col=2)

    fig.update_layout(height=800, width=800, title_text="Sentiment Analysis Overview")
    st.plotly_chart(fig)

if __name__ == "__main__":
    render_dashboard_analytics()