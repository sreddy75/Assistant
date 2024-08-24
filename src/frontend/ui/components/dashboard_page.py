import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from ui.components.utils import BACKEND_URL

def fetch_data(endpoint):
    try:
        response = requests.get(f"{BACKEND_URL}{endpoint}")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"Failed to fetch data from {endpoint}: {str(e)}")
        return None

def safe_get(data, *keys, default=None):
    for key in keys:
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return default
    return data

def format_metric(value, format_string="{:.2f}", suffix=""):
    if value is None:
        return "N/A"
    try:
        return f"{format_string.format(value)}{suffix}"
    except (ValueError, TypeError):
        return str(value) + suffix

def render_dashboard_analytics():    

    # Fetch data from all relevant endpoints
    sentiment_analysis = fetch_data("/api/v1/analytics/sentiment-analysis")
    feedback_analysis = fetch_data("/api/v1/analytics/feedback-analysis")
    user_engagement = fetch_data("/api/v1/analytics/user-engagement")
    interaction_metrics = fetch_data("/api/v1/analytics/interaction-metrics")
    quality_metrics = fetch_data("/api/v1/analytics/quality-metrics")
    usage_patterns = fetch_data("/api/v1/analytics/usage-patterns")

    if all(data is None for data in [sentiment_analysis, feedback_analysis, user_engagement, interaction_metrics, quality_metrics, usage_patterns]):
        st.warning("Failed to fetch data from the API. Please check the server connection.")
        return

    # Key Insights and User Engagement at the top
    col1, col2 = st.columns(2)

    with col1:
        st.header("Key Insights")
        insights = []

        if user_engagement:
            user_growth = safe_get(user_engagement, 'user_growth')
            if user_growth and len(user_growth) > 1:
                growth = user_growth[-1]['new_users'] - user_growth[0]['new_users']
                insights.append(f"User base growth: {growth} users")
        
        if interaction_metrics:
            total_queries = safe_get(interaction_metrics, 'query_volume', 'total')
            if total_queries is not None:
                insights.append(f"Total queries: {total_queries}")
        
        if quality_metrics:
            satisfaction_score = safe_get(quality_metrics, 'satisfaction_score')
            if satisfaction_score is not None:
                insights.append(f"User satisfaction: {satisfaction_score:.2f}%")

        if usage_patterns:
            feature_adoption = safe_get(usage_patterns, 'feature_adoption')
            if feature_adoption:
                top_feature = max(feature_adoption, key=lambda x: x['count'])['feature']
                insights.append(f"Top feature: '{top_feature}'")

        if insights:
            for insight in insights:
                st.write("• " + insight)
        else:
            st.warning("Not enough data to generate insights at this time.")

    with col2:
        st.header("Active Users")
        if user_engagement:
            daily_active = safe_get(user_engagement, 'active_users', 'daily')
            weekly_active = safe_get(user_engagement, 'active_users', 'weekly')
            monthly_active = safe_get(user_engagement, 'active_users', 'monthly')

            metric_col1, metric_col2, metric_col3 = st.columns(3)
            with metric_col1:
                st.metric("Daily", format_metric(daily_active, "{:.0f}"))
            with metric_col2:
                st.metric("Weekly", format_metric(weekly_active, "{:.0f}"))
            with metric_col3:
                st.metric("Monthly", format_metric(monthly_active, "{:.0f}"))
        else:
            st.warning("User engagement data is not available.")

    # User Growth and Interaction Metrics
    col1, col2 = st.columns(2)
    
    with col1:
        st.header("User Growth")
        if user_engagement:
            user_growth = safe_get(user_engagement, 'user_growth', default=[])
            if user_growth:
                user_growth_df = pd.DataFrame(user_growth)
                user_growth_df['date'] = pd.to_datetime(user_growth_df['date'])
                fig_user_growth = px.area(user_growth_df, x='date', y='new_users', title="User Growth Over Time")
                st.plotly_chart(fig_user_growth)
            else:
                st.warning("User growth data is not available.")

    with col2:
        st.header("Interaction Metrics")
        if interaction_metrics:
            col1, col2, col3 = st.columns(3)
            with col1:
                total_queries = safe_get(interaction_metrics, 'query_volume', 'total')
                st.metric("Total Queries", format_metric(total_queries, "{:.0f}"))
            with col2:
                avg_response_time = safe_get(interaction_metrics, 'avg_response_time')
                st.metric("Avg Response Time", format_metric(avg_response_time, "{:.2f}", "s"))
            with col3:
                avg_session_duration = safe_get(interaction_metrics, 'avg_session_duration')
                st.metric("Avg Session Duration", format_metric(avg_session_duration, "{:.2f}", "s"))

    # Query Volume Trend
    st.header("Query Volume Trend")
    query_trend = safe_get(interaction_metrics, 'query_volume', 'recent_trend', default=[])
    if query_trend:
        query_trend_df = pd.DataFrame(query_trend)
        query_trend_df['date'] = pd.to_datetime(query_trend_df['date'])
        fig_query_trend = px.line(query_trend_df, x='date', y='count', title="Query Volume Trend")
        st.plotly_chart(fig_query_trend)
    else:
        st.warning("Query volume trend data is not available.")
        
    # User Retention Visualization
    st.header("User Retention")
    if user_engagement:
        user_retention = safe_get(user_engagement, 'user_retention', default=[])
        if user_retention:
            retention_df = pd.DataFrame(user_retention)
            
            if 'cohort' in retention_df.columns and 'retention_rate' in retention_df.columns:
                if 'week' in retention_df.columns:
                    fig_retention = px.imshow(
                        retention_df.pivot(columns='cohort', values='retention_rate', index='week'),
                        title="User Retention Heatmap",
                        labels=dict(x="Cohort", y="Week", color="Retention Rate")
                    )
                else:
                    fig_retention = px.imshow(
                        retention_df.pivot(columns='cohort', values='retention_rate'),
                        title="User Retention Heatmap",
                        labels=dict(x="Cohort", y="Period", color="Retention Rate")
                    )
                st.plotly_chart(fig_retention)
            elif 'cohort' in retention_df.columns:
                fig_retention = px.line(
                    retention_df, 
                    x='cohort', 
                    y=retention_df.columns.drop('cohort'), 
                    title="User Retention Over Time"
                )
                st.plotly_chart(fig_retention)
            else:
                st.write("User Retention Data:")
                st.write(retention_df)
        else:
            st.warning("User retention data is not available.")

    # Quality Metrics
    st.header("Quality Metrics")
    if quality_metrics and sentiment_analysis:
        col1, col2 = st.columns(2)
        with col1:
            satisfaction_score = safe_get(quality_metrics, 'satisfaction_score')
            if satisfaction_score is not None:
                fig_satisfaction = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=satisfaction_score,
                    title={'text': "Satisfaction Score"},
                    gauge={'axis': {'range': [None, 100]},
                           'steps': [
                               {'range': [0, 50], 'color': "lightgray"},
                               {'range': [50, 80], 'color': "gray"}],
                           'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 80}}))
                st.plotly_chart(fig_satisfaction)
            else:
                st.warning("Satisfaction score data is not available.")

        with col2:
            avg_sentiment = safe_get(sentiment_analysis, 'average_sentiment_score')
            st.metric("Average Sentiment Score", format_metric(avg_sentiment, "{:.2f}"))

        # Word Cloud
        word_cloud_data = safe_get(quality_metrics, 'word_cloud_data', default={})
        if word_cloud_data:
            wordcloud = WordCloud(width=800, height=400, background_color='white').generate_from_frequencies(word_cloud_data)
            plt.figure(figsize=(10, 5))
            plt.imshow(wordcloud, interpolation='bilinear')
            plt.axis('off')
            st.pyplot(plt)
        else:
            st.warning("No word cloud data available.")

        # Sentiment Trend
        sentiment_trend = safe_get(quality_metrics, 'sentiment_trend', default=[])
        if sentiment_trend:
            sentiment_trend_df = pd.DataFrame(sentiment_trend)
            sentiment_trend_df['date'] = pd.to_datetime(sentiment_trend_df['date'])
            fig_sentiment_trend = px.line(sentiment_trend_df, x='date', y='sentiment', title="Sentiment Trend Over Time")
            st.plotly_chart(fig_sentiment_trend)
        else:
            st.warning("Sentiment trend data is not available.")

    # Usage Patterns
    st.header("Usage Patterns")
    if usage_patterns:
        # Popular Topics
        popular_topics = safe_get(usage_patterns, 'popular_topics', default=[])
        if popular_topics:
            popular_topics_df = pd.DataFrame(popular_topics)
            fig_popular_topics = px.treemap(popular_topics_df, path=['topic'], values='count', title="Popular Topics")
            st.plotly_chart(fig_popular_topics)
        else:
            st.warning("Popular topics data is not available.")

        # Peak Usage Times
        peak_usage = safe_get(usage_patterns, 'peak_usage', default=[])
        if peak_usage:
            peak_usage_df = pd.DataFrame(peak_usage)
            fig_peak_usage = px.bar(peak_usage_df, x='hour', y='count', title="Peak Usage Times")
            st.plotly_chart(fig_peak_usage)
        else:
            st.warning("Peak usage data is not available.")

        # Feature Adoption
        feature_adoption = safe_get(usage_patterns, 'feature_adoption', default=[])
        if feature_adoption:
            feature_adoption_df = pd.DataFrame(feature_adoption)
            fig_feature_adoption = px.bar(feature_adoption_df, x='feature', y='count', title="Feature Adoption")
            st.plotly_chart(fig_feature_adoption)
        else:
            st.warning("Feature adoption data is not available.")

    # Feedback Analysis
    st.header("Feedback Analysis")
    if feedback_analysis:
        col1, col2 = st.columns(2)
        with col1:
            avg_sentiment = safe_get(feedback_analysis, 'average_sentiment')
            st.metric("Average Sentiment", format_metric(avg_sentiment, "{:.2f}"))
        with col2:
            feedback_count = safe_get(feedback_analysis, 'feedback_count')
            st.metric("Feedback Count", format_metric(feedback_count, "{:.0f}"))

        # Sentiment Distribution
        sentiment_distribution = safe_get(feedback_analysis, 'sentiment_distribution', default={})
        if sentiment_distribution:
            fig_sentiment_dist = px.pie(
                values=list(sentiment_distribution.values()),
                names=list(sentiment_distribution.keys()),
                title="Sentiment Distribution"
            )
            st.plotly_chart(fig_sentiment_dist)
        else:
            st.warning("Sentiment distribution data is not available.")

        # Top Keywords
        top_keywords = safe_get(feedback_analysis, 'top_keywords', default={})
        if top_keywords:
            top_keywords_df = pd.DataFrame(list(top_keywords.items()), columns=['keyword', 'score'])
            fig_top_keywords = px.bar(top_keywords_df.head(10), x='keyword', y='score', title="Top Keywords in Feedback")
            st.plotly_chart(fig_top_keywords)
        else:
            st.warning("Top keywords data is not available.")

if __name__ == "__main__":
    render_dashboard_analytics()