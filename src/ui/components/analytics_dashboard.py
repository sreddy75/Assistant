import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import traceback
import requests
from ui.components.utils import BACKEND_URL

def fetch_data(endpoint):
    response = requests.get(f"{BACKEND_URL}{endpoint}")
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to fetch data from {endpoint}: {response.status_code}")
        return None

def render_analytics_dashboard():
    st.header("Analytics Dashboard")

    sentiment_analysis = fetch_data("/ap1/v1//sentiment-analysis")
    feedback_analysis = fetch_data("/api/v1/feedback-analysis")
    
    if sentiment_analysis is None or feedback_analysis is None:
        st.warning("Failed to fetch data from the API. Please check the server connection.")
        return

    if "error" in sentiment_analysis:
        st.warning(f"No vote data available: {sentiment_analysis['error']}")
        st.info("The analytics dashboard will populate with data once users start providing feedback.")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            if 'average_sentiment_score' in sentiment_analysis:
                st.metric("Average Sentiment Score", f"{sentiment_analysis['average_sentiment_score']:.2f}")
        with col2:
            if 'average_usefulness_rating' in sentiment_analysis:
                st.metric("Average Usefulness Rating", f"{sentiment_analysis['average_usefulness_rating']:.2f}")
        with col3:
            if 'upvote_percentage' in sentiment_analysis:
                st.metric("Upvote Percentage", f"{sentiment_analysis['upvote_percentage']:.2f}%")
    
    try:
        plot_sentiment_analysis(sentiment_analysis)
    except Exception as e:
        st.error(f"Error plotting sentiment analysis: {str(e)}")
        print(f"Error details: {traceback.format_exc()}")
    
    if "error" not in feedback_analysis:
        st.subheader("Feedback Analysis")
        col1, col2 = st.columns(2)
        with col1:
            st.write("Top Keywords")
            df_keywords = pd.DataFrame.from_dict(feedback_analysis['top_keywords'], orient='index', columns=['score'])
            df_keywords = df_keywords.sort_values('score', ascending=False).head(10)
            st.bar_chart(df_keywords)
        
        with col2:
            st.write("Sentiment Distribution")
            sentiment_dist = feedback_analysis['sentiment_distribution']
            fig = px.pie(values=list(sentiment_dist.values()), names=list(sentiment_dist.keys()))
            st.plotly_chart(fig)
        
        st.write("Topics")
        for topic in feedback_analysis['topics']:
            st.write(topic)
        
        st.metric("Feedback Count", feedback_analysis['feedback_count'])
        st.metric("Average Sentiment", f"{feedback_analysis['average_sentiment']:.2f}")
        st.metric("Sentiment-Usefulness Correlation", f"{feedback_analysis['sentiment_usefulness_correlation']:.2f}")
    
    # Fetch and display user events summary
    event_summary = fetch_data("/event-summary")
    if event_summary:
        st.subheader("Event Summary")
        df_events = pd.DataFrame.from_dict(event_summary, orient='index', columns=['count'])
        st.bar_chart(df_events)

def plot_sentiment_analysis(analysis):
    if "error" in analysis:
        st.warning("No data available for sentiment analysis plot.")
        return

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Daily Average Sentiment", "Distribution of Usefulness Ratings",
                        "Upvote vs Downvote Percentage", "Distribution of Sentiment Scores")
    )

    # Plot daily sentiment if available
    if 'daily_data' in analysis and 'sentiment_score' in analysis['daily_data']:
        daily_sentiment = pd.DataFrame.from_dict(analysis['daily_data']['sentiment_score'], orient='index', columns=['sentiment_score'])
        daily_sentiment.index = pd.to_datetime(daily_sentiment.index)
        fig.add_trace(go.Scatter(x=daily_sentiment.index, y=daily_sentiment['sentiment_score'], mode='lines'), row=1, col=1)

    # Plot usefulness distribution if available
    if 'usefulness_rating_distribution' in analysis:
        usefulness = pd.DataFrame.from_dict(analysis['usefulness_rating_distribution'], orient='index', columns=['count'])
        fig.add_trace(go.Bar(x=usefulness.index, y=usefulness['count']), row=1, col=2)

    # Plot upvote percentage if available
    if 'upvote_percentage' in analysis:
        fig.add_trace(go.Bar(x=['Upvotes', 'Downvotes'], y=[analysis['upvote_percentage'], 100 - analysis['upvote_percentage']]), row=2, col=1)

    # Plot sentiment score distribution if available
    if 'sentiment_score_distribution' in analysis:
        sentiment = pd.DataFrame.from_dict(analysis['sentiment_score_distribution'], orient='index', columns=['count'])
        fig.add_trace(go.Bar(x=sentiment.index, y=sentiment['count']), row=2, col=2)

    fig.update_layout(height=800, width=800, title_text="Sentiment Analysis Overview")
    st.plotly_chart(fig)

if __name__ == "__main__":
    render_analytics_dashboard()