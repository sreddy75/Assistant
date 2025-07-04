import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from utils.api import fetch_data
from utils.helpers import safe_get, format_metric
import json

def render_analytics_dashboard():
    st.title("Analytics Dashboard")

    if st.button("Refresh Analytics"):
        st.cache_data.clear()
        st.success("Cache cleared. Fetching fresh data...")

    analytics_data = get_analytics_data()

    if isinstance(analytics_data, dict) and 'error' in analytics_data:
        st.error(f"Failed to fetch analytics data: {analytics_data['error']}")
        return

    col1, col2 = st.columns(2)

    with col1:
        render_key_insights(analytics_data)

    with col2:
        render_active_users(analytics_data)

    st.header("User Growth and Interaction")
    col1, col2 = st.columns(2)

    with col1:
        render_user_growth(analytics_data)

    with col2:
        render_interaction_metrics(analytics_data)

    render_query_volume_trend(analytics_data)
    render_user_retention(analytics_data)
    render_quality_metrics(analytics_data)
    render_sentiment_trend(analytics_data)
    render_usage_patterns(analytics_data)
    render_feature_adoption(analytics_data)
    render_feedback_analysis(analytics_data)

@st.cache_data(ttl=300)
def get_analytics_data():
    try:
        all_analytics = fetch_data("/api/v1/analytics/all-analytics")
        
        if isinstance(all_analytics, str):
            all_analytics = json.loads(all_analytics)
        
        if not isinstance(all_analytics, dict):
            raise ValueError("Unexpected data format from API")
        
        return all_analytics
    except json.JSONDecodeError:
        return {"error": "Failed to parse analytics data"}
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}

def render_key_insights(data):
    st.subheader("Key Insights")
    insights = []

    user_engagement = data.get("user_engagement", {})
    interaction_metrics = data.get("interaction_metrics", {})
    quality_metrics = data.get("quality_metrics", {})
    usage_patterns = data.get("usage_patterns", {})

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
        feature_adoption = safe_get(usage_patterns, 'feature_adoption', default=[])
        if feature_adoption:
            top_feature = max(feature_adoption, key=lambda x: x['count'])['feature']
            insights.append(f"Top feature: '{top_feature}'")

    if insights:
        for insight in insights:
            st.write("• " + insight)
    else:
        st.warning("Not enough data to generate insights at this time.")

def render_active_users(data):
    user_engagement = data.get("user_engagement", {})
    st.subheader("Active Users")
    if user_engagement:
        daily_active = safe_get(user_engagement, 'active_users', 'daily')
        weekly_active = safe_get(user_engagement, 'active_users', 'weekly')
        monthly_active = safe_get(user_engagement, 'active_users', 'monthly')

        st.write(f"Daily: {format_metric(daily_active, '{:.0f}')}")
        st.write(f"Weekly: {format_metric(weekly_active, '{:.0f}')}")
        st.write(f"Monthly: {format_metric(monthly_active, '{:.0f}')}")
    else:
        st.warning("User engagement data is not available.")

def render_user_growth(data):
    user_engagement = data.get("user_engagement", {})
    st.subheader("User Growth")
    if user_engagement:
        user_growth = safe_get(user_engagement, 'user_growth', default=[])
        if user_growth:
            user_growth_df = pd.DataFrame(user_growth)
            user_growth_df['date'] = pd.to_datetime(user_growth_df['date'])
            fig_user_growth = px.area(user_growth_df, x='date', y='new_users', title="User Growth Over Time")
            st.plotly_chart(fig_user_growth, use_container_width=True)
        else:
            st.warning("User growth data is not available.")

def render_interaction_metrics(data):
    interaction_metrics = data.get("interaction_metrics", {})
    st.subheader("Interaction Metrics")
    if interaction_metrics:
        total_queries = safe_get(interaction_metrics, 'query_volume', 'total')
        avg_response_time = safe_get(interaction_metrics, 'avg_response_time')
        avg_session_duration = safe_get(interaction_metrics, 'avg_session_duration')

        st.write(f"Total Queries: {format_metric(total_queries, '{:.0f}')}")
        st.write(f"Avg Response Time: {format_metric(avg_response_time, '{:.2f}', 's')}")
        st.write(f"Avg Session Duration: {format_metric(avg_session_duration, '{:.2f}', 's')}")

def render_query_volume_trend(data):
    interaction_metrics = data.get("interaction_metrics", {})
    st.header("Query Volume Trend")
    query_trend = safe_get(interaction_metrics, 'query_volume', 'recent_trend', default=[])
    if query_trend:
        query_trend_df = pd.DataFrame(query_trend)
        query_trend_df['date'] = pd.to_datetime(query_trend_df['date'])
        fig_query_trend = px.line(query_trend_df, x='date', y='count', title="Query Volume Trend")
        st.plotly_chart(fig_query_trend, use_container_width=True)
    else:
        st.warning("Query volume trend data is not available.")

def render_user_retention(data):
    user_engagement = data.get("user_engagement", {})
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
                st.plotly_chart(fig_retention, use_container_width=True)
            elif 'cohort' in retention_df.columns:
                fig_retention = px.line(
                    retention_df, 
                    x='cohort', 
                    y=retention_df.columns.drop('cohort'), 
                    title="User Retention Over Time"
                )
                st.plotly_chart(fig_retention, use_container_width=True)
            else:
                st.write("User Retention Data:")
                st.write(retention_df)
        else:
            st.warning("User retention data is not available.")

def render_quality_metrics(data):
    quality_metrics = data.get("quality_metrics", {})
    sentiment_analysis = data.get("sentiment_analysis", {})
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
                st.plotly_chart(fig_satisfaction, use_container_width=True)
            else:
                st.warning("Satisfaction score data is not available.")

        with col2:
            avg_sentiment = safe_get(sentiment_analysis, 'average_sentiment_score')
            st.metric("Average Sentiment Score", format_metric(avg_sentiment, "{:.2f}"))

            word_cloud_data = safe_get(quality_metrics, 'word_cloud_data', default={})
            if word_cloud_data:
                wordcloud = WordCloud(width=400, height=200, background_color='white').generate_from_frequencies(word_cloud_data)
                plt.figure(figsize=(5, 2.5))
                plt.imshow(wordcloud, interpolation='bilinear')
                plt.axis('off')
                st.pyplot(plt)
            else:
                st.warning("No word cloud data available.")

def render_sentiment_trend(data):
    quality_metrics = data.get("quality_metrics", {})
    st.header("Sentiment Trend")
    sentiment_trend = safe_get(quality_metrics, 'sentiment_trend', default=[])
    if sentiment_trend:
        sentiment_trend_df = pd.DataFrame(sentiment_trend)
        sentiment_trend_df['date'] = pd.to_datetime(sentiment_trend_df['date'])
        fig_sentiment_trend = px.line(sentiment_trend_df, x='date', y='sentiment', title="Sentiment Trend Over Time")
        st.plotly_chart(fig_sentiment_trend, use_container_width=True)
    else:
        st.warning("Sentiment trend data is not available.")

def render_usage_patterns(data):
    usage_patterns = data.get("usage_patterns", {})
    st.header("Usage Patterns")
    if usage_patterns:
        col1, col2 = st.columns(2)

        with col1:
            popular_topics = safe_get(usage_patterns, 'popular_topics', default=[])
            if popular_topics:
                popular_topics_df = pd.DataFrame(popular_topics)
                fig_popular_topics = px.treemap(popular_topics_df, path=['topic'], values='count', title="Popular Topics")
                st.plotly_chart(fig_popular_topics, use_container_width=True)
            else:
                st.warning("Popular topics data is not available.")

        with col2:
            peak_usage = safe_get(usage_patterns, 'peak_usage', default=[])
            if peak_usage:
                peak_usage_df = pd.DataFrame(peak_usage)
                fig_peak_usage = px.bar(peak_usage_df, x='hour', y='count', title="Peak Usage Times")
                st.plotly_chart(fig_peak_usage, use_container_width=True)
            else:
                st.warning("Peak usage data is not available.")

def render_feature_adoption(data):
    usage_patterns = data.get("usage_patterns", {})
    st.header("Feature Adoption")
    feature_adoption = safe_get(usage_patterns, 'feature_adoption', default=[])
    if feature_adoption:
        feature_adoption_df = pd.DataFrame(feature_adoption)
        fig_feature_adoption = px.bar(feature_adoption_df, x='feature', y='count', title="Feature Adoption")
        st.plotly_chart(fig_feature_adoption, use_container_width=True)
    else:
        st.warning("Feature adoption data is not available.")

def render_feedback_analysis(data):
    feedback_analysis = data.get("feedback_analysis", {})
    st.header("Feedback Analysis")
    if feedback_analysis:
        col1, col2 = st.columns(2)
        with col1:
            avg_sentiment = safe_get(feedback_analysis, 'average_sentiment')
            st.metric("Average Sentiment", format_metric(avg_sentiment, "{:.2f}"))
        with col2:
            feedback_count = safe_get(feedback_analysis, 'feedback_count')
            st.metric("Feedback Count", format_metric(feedback_count, "{:.0f}"))

        sentiment_distribution = safe_get(feedback_analysis, 'sentiment_distribution', default={})
        if sentiment_distribution:
            fig_sentiment_dist = px.pie(
                values=list(sentiment_distribution.values()),
                names=list(sentiment_distribution.keys()),
                title="Sentiment Distribution"
            )
            st.plotly_chart(fig_sentiment_dist, use_container_width=True)
        else:
            st.warning("Sentiment distribution data is not available.")

        top_keywords = safe_get(feedback_analysis, 'top_keywords', default={})
        if top_keywords:
            top_keywords_df = pd.DataFrame(list(top_keywords.items()), columns=['keyword', 'score'])
            fig_top_keywords = px.bar(top_keywords_df.head(10), x='keyword', y='score', title="Top Keywords in Feedback")
            st.plotly_chart(fig_top_keywords, use_container_width=True)
        else:
            st.warning("Top keywords data is not available.")

if __name__ == "__main__":
    render_analytics_dashboard()