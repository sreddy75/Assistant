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

def render_analytics_dashboard():
    st.header("Analytics Dashboard")

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

    # Feedback Analysis Section
    st.subheader("Feedback Analysis")
    if feedback_analysis is None:
        st.warning("No feedback analysis data available.")
    else:
        display_feedback_analysis(feedback_analysis)

    # User Events Section
    st.subheader("User Events")
    if user_events is None:
        st.warning("No user events data available.")
    else:
        display_user_events(user_events)

    # Event Summary Section
    st.subheader("Event Summary")
    if event_summary is None:
        st.warning("No event summary data available.")
    else:
        display_event_summary(event_summary)

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

def display_feedback_analysis(data):
    col1, col2 = st.columns(2)
    with col1:
        st.write("Top Keywords")
        if 'top_keywords' in data and data['top_keywords']:
            df_keywords = pd.DataFrame.from_dict(data['top_keywords'], orient='index', columns=['score'])
            df_keywords = df_keywords.sort_values('score', ascending=False).head(10)
            st.bar_chart(df_keywords)
        else:
            st.info("No top keywords data available")
    
    with col2:
        st.write("Sentiment Distribution")
        if 'sentiment_distribution' in data and data['sentiment_distribution']:
            sentiment_dist = data['sentiment_distribution']
            fig = px.pie(values=list(sentiment_dist.values()), names=list(sentiment_dist.keys()))
            st.plotly_chart(fig)
        else:
            st.info("No sentiment distribution data available")
    
    if 'topics' in data and data['topics']:
        st.write("Topics")
        for topic in data['topics']:
            st.write(topic)
    else:
        st.info("No topics data available")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if 'feedback_count' in data:
            st.metric("Feedback Count", data['feedback_count'])
    with col2:
        if 'average_sentiment' in data:
            st.metric("Average Sentiment", f"{data['average_sentiment']:.2f}")
    with col3:
        if 'sentiment_usefulness_correlation' in data and data['sentiment_usefulness_correlation'] is not None:
            st.metric("Sentiment-Usefulness Correlation", f"{data['sentiment_usefulness_correlation']:.2f}")
        else:
            st.info("Sentiment-Usefulness Correlation not available")

def display_user_events(data):
    if isinstance(data, list) and len(data) > 0:
        df_events = pd.DataFrame(data)
        st.dataframe(df_events)
    else:
        st.info("No user events data available")

def display_event_summary(data):
    if isinstance(data, dict) and len(data) > 0:
        df_summary = pd.DataFrame.from_dict(data, orient='index', columns=['count'])
        st.bar_chart(df_summary)
    else:
        st.info("No event summary data available")

def plot_sentiment_analysis(analysis):
    if not isinstance(analysis, dict) or len(analysis) == 0:
        st.info("No sentiment analysis data available for plotting")
        return

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Daily Average Sentiment", "Distribution of Usefulness Ratings",
                        "Upvote vs Downvote Percentage", "Distribution of Sentiment Scores")
    )

    if 'daily_data' in analysis and 'sentiment_score' in analysis['daily_data']:
        daily_sentiment = pd.DataFrame.from_dict(analysis['daily_data']['sentiment_score'], orient='index', columns=['sentiment_score'])
        daily_sentiment.index = pd.to_datetime(daily_sentiment.index)
        fig.add_trace(go.Scatter(x=daily_sentiment.index, y=daily_sentiment['sentiment_score'], mode='lines'), row=1, col=1)

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
    render_analytics_dashboard()