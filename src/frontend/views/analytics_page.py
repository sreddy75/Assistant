import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from utils.api import fetch_data
from utils.helpers import safe_get, format_metric
from utils.auth import is_authenticated

def render_analytics_page():
    if not is_authenticated():
        st.warning("Please log in to view analytics.")
        return

    if not st.session_state.get('is_admin', False):
        st.error("You do not have permission to view this page.")
        return

    st.title("Analytics Dashboard")

    # Fetch all analytics data at once
    all_analytics = fetch_analytics_data()

    if all_analytics:
        render_dashboard(all_analytics)

def fetch_analytics_data():
    with st.spinner("Loading analytics data..."):
        all_analytics = fetch_data("/api/v1/analytics/all-analytics")

    if all_analytics is None:
        st.error("Failed to fetch analytics data. Please try again later.")
        if st.button("Retry"):
            st.experimental_rerun()
        return None

    if isinstance(all_analytics, dict) and 'detail' in all_analytics:
        st.error(f"Failed to fetch analytics data: {all_analytics['detail']}")
        if st.button("Retry"):
            st.experimental_rerun()
        return None

    if not isinstance(all_analytics, dict) or not all_analytics:
        st.error("Received invalid analytics data. Please try again later.")
        if st.button("Retry"):
            st.experimental_rerun()
        return None

    return all_analytics

def render_dashboard(all_analytics):
    st.header("User Engagement")
    col1, col2 = st.columns(2)
    with col1:
        render_key_insights(all_analytics)
    with col2:
        render_active_users(all_analytics.get('user_engagement', {}))

    st.header("User Growth and Interaction")
    col1, col2 = st.columns(2)
    with col1:
        render_user_growth(all_analytics.get('user_engagement', {}))
    with col2:
        render_interaction_metrics(all_analytics.get('interaction_metrics', {}))

    render_query_volume_trend(all_analytics.get('interaction_metrics', {}))
    render_user_retention(all_analytics.get('user_retention', {}))
    render_quality_metrics(all_analytics.get('quality_metrics', {}), all_analytics.get('sentiment_analysis', {}))
    render_sentiment_trend(all_analytics.get('quality_metrics', {}))
    render_usage_patterns(all_analytics.get('usage_patterns', {}))
    render_feature_adoption(all_analytics.get('feature_usage', {}))
    render_feedback_analysis(all_analytics.get('feedback_analysis', {}))
    render_user_segmentation(all_analytics.get('user_segmentation', {}))
    render_conversion_funnel(all_analytics.get('conversion_funnel', {}))
    render_churn_rate(all_analytics.get('churn_rate', {}))

def render_key_insights(all_analytics):
    st.subheader("Key Insights")
    insights = []

    user_engagement = all_analytics.get('user_engagement', {})
    interaction_metrics = all_analytics.get('interaction_metrics', {})
    quality_metrics = all_analytics.get('quality_metrics', {})
    usage_patterns = all_analytics.get('usage_patterns', {})

    if user_engagement:
        user_growth = safe_get(user_engagement, 'user_growth', default=[])
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
            st.info(insight)
    else:
        st.warning("Not enough data to generate insights at this time.")

def render_active_users(user_engagement):
    st.subheader("Active Users")
    if user_engagement:
        daily_active = safe_get(user_engagement, 'active_users', 'daily')
        weekly_active = safe_get(user_engagement, 'active_users', 'weekly')
        monthly_active = safe_get(user_engagement, 'active_users', 'monthly')

        col1, col2, col3 = st.columns(3)
        col1.metric("Daily Active Users", format_metric(daily_active, '{:.0f}'))
        col2.metric("Weekly Active Users", format_metric(weekly_active, '{:.0f}'))
        col3.metric("Monthly Active Users", format_metric(monthly_active, '{:.0f}'))
    else:
        st.warning("User engagement data is not available.")

def render_user_growth(user_engagement):
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

def render_interaction_metrics(interaction_metrics):
    st.subheader("Interaction Metrics")
    if interaction_metrics:
        total_queries = safe_get(interaction_metrics, 'query_volume', 'total')
        avg_response_time = safe_get(interaction_metrics, 'avg_response_time')
        avg_session_duration = safe_get(interaction_metrics, 'avg_session_duration')

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Queries", format_metric(total_queries, '{:.0f}'))
        col2.metric("Avg Response Time", format_metric(avg_response_time, '{:.2f}', 's'))
        col3.metric("Avg Session Duration", format_metric(avg_session_duration, '{:.2f}', 's'))

def render_query_volume_trend(interaction_metrics):
    st.subheader("Query Volume Trend")
    query_trend = safe_get(interaction_metrics, 'query_volume', 'recent_trend', default=[])
    if query_trend:
        query_trend_df = pd.DataFrame(query_trend)
        query_trend_df['date'] = pd.to_datetime(query_trend_df['date'])
        fig_query_trend = px.line(query_trend_df, x='date', y='count', title="Query Volume Trend")
        st.plotly_chart(fig_query_trend, use_container_width=True)
    else:
        st.warning("Query volume trend data is not available.")

def render_user_retention(user_retention):
    st.subheader("User Retention")
    if user_retention:
        retention_df = pd.DataFrame(user_retention)
        if 'cohort' in retention_df.columns and 'retention_rate' in retention_df.columns:
            fig_retention = px.line(retention_df, x='cohort', y='retention_rate', title="User Retention Over Time")
            st.plotly_chart(fig_retention, use_container_width=True)
        else:
            st.write("User Retention Data:")
            st.write(retention_df)
    else:
        st.warning("User retention data is not available.")

def render_quality_metrics(quality_metrics, sentiment_analysis):
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

            # Word Cloud
            word_cloud_data = safe_get(quality_metrics, 'word_cloud_data', default={})
            if word_cloud_data:
                wordcloud = WordCloud(width=400, height=200, background_color='white').generate_from_frequencies(word_cloud_data)
                plt.figure(figsize=(5, 2.5))
                plt.imshow(wordcloud, interpolation='bilinear')
                plt.axis('off')
                st.pyplot(plt)
            else:
                st.warning("No word cloud data available.")

def render_sentiment_trend(quality_metrics):
    st.header("Sentiment Trend")
    sentiment_trend = safe_get(quality_metrics, 'sentiment_trend', default=[])
    if sentiment_trend:
        sentiment_trend_df = pd.DataFrame(sentiment_trend)
        sentiment_trend_df['date'] = pd.to_datetime(sentiment_trend_df['date'])
        fig_sentiment_trend = px.line(sentiment_trend_df, x='date', y='sentiment', title="Sentiment Trend Over Time")
        st.plotly_chart(fig_sentiment_trend, use_container_width=True)
    else:
        st.warning("Sentiment trend data is not available.")

def render_usage_patterns(usage_patterns):
    st.header("Usage Patterns")
    if usage_patterns:
        col1, col2 = st.columns(2)

        with col1:
            # Popular Topics
            popular_topics = safe_get(usage_patterns, 'popular_topics', default=[])
            if popular_topics:
                popular_topics_df = pd.DataFrame(popular_topics)
                fig_popular_topics = px.treemap(popular_topics_df, path=['topic'], values='count', title="Popular Topics")
                st.plotly_chart(fig_popular_topics, use_container_width=True)
            else:
                st.warning("Popular topics data is not available.")

        with col2:
            # Peak Usage Times
            peak_usage = safe_get(usage_patterns, 'peak_usage', default=[])
            if peak_usage:
                peak_usage_df = pd.DataFrame(peak_usage)
                fig_peak_usage = px.bar(peak_usage_df, x='hour', y='count', title="Peak Usage Times")
                st.plotly_chart(fig_peak_usage, use_container_width=True)
            else:
                st.warning("Peak usage data is not available.")

def render_feature_adoption(feature_usage):
    st.header("Feature Adoption")
    if feature_usage:
        feature_usage_df = pd.DataFrame(feature_usage)
        fig_feature_adoption = px.bar(feature_usage_df, x='feature', y='usage_count', title="Feature Adoption")
        st.plotly_chart(fig_feature_adoption, use_container_width=True)
    else:
        st.warning("Feature adoption data is not available.")

def render_feedback_analysis(feedback_analysis):
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
            st.plotly_chart(fig_sentiment_dist, use_container_width=True)
        else:
            st.warning("Sentiment distribution data is not available.")

        # Top Keywords
        top_keywords = safe_get(feedback_analysis, 'top_keywords', default={})
        if top_keywords:
            top_keywords_df = pd.DataFrame(list(top_keywords.items()), columns=['keyword', 'score'])
            fig_top_keywords = px.bar(top_keywords_df.head(10), x='keyword', y='score', title="Top Keywords in Feedback")
            st.plotly_chart(fig_top_keywords, use_container_width=True)
        else:
            st.warning("Top keywords data is not available.")

def render_user_segmentation(user_segmentation):
    st.header("User Segmentation")
    if user_segmentation:
        col1, col2 = st.columns(2)
        with col1:
            active_users = safe_get(user_segmentation, 'active_users')
            inactive_users = safe_get(user_segmentation, 'inactive_users')
            fig_active_inactive = px.pie(
                values=[active_users, inactive_users],
                names=['Active', 'Inactive'],
                title="Active vs Inactive Users"
            )
            st.plotly_chart(fig_active_inactive, use_container_width=True)
        
        with col2:
            engagement_data = {
                'High': safe_get(user_segmentation, 'high_engagement'),
                'Medium': safe_get(user_segmentation, 'medium_engagement'),
                'Low': safe_get(user_segmentation, 'low_engagement')
            }
            fig_engagement = px.bar(
                x=list(engagement_data.keys()),
                y=list(engagement_data.values()),
                title="User Engagement Levels"
            )
            st.plotly_chart(fig_engagement, use_container_width=True)
    else:
        st.warning("User segmentation data is not available.")

def render_conversion_funnel(conversion_funnel):
    st.header("Conversion Funnel")
    if conversion_funnel:
        funnel_stages = ['total_visitors', 'signed_up', 'active_users', 'paying_users']
        funnel_values = [safe_get(conversion_funnel, stage) for stage in funnel_stages]
        funnel_labels = ['Total Visitors', 'Signed Up', 'Active Users', 'Paying Users']
        
        fig_funnel = go.Figure(go.Funnel(
            y=funnel_labels,
            x=funnel_values,
            textinfo="value+percent initial"
        ))
        fig_funnel.update_layout(title_text="Conversion Funnel")
        st.plotly_chart(fig_funnel, use_container_width=True)
    else:
        st.warning("Conversion funnel data is not available.")

def render_churn_rate(churn_rate):
    st.header("Churn Rate")
    if churn_rate:
        col1, col2 = st.columns(2)
        with col1:
            churn_rate_value = safe_get(churn_rate, 'churn_rate')
            if churn_rate_value is not None:
                st.metric("Churn Rate", f"{churn_rate_value:.2f}%")
            else:
                st.metric("Churn Rate", "N/A")
        with col2:
            fig_churn = go.Figure(go.Indicator(
                mode="gauge+number",
                value=safe_get(churn_rate, 'churn_rate', 0),
                title={'text': "Churn Rate"},
                gauge={'axis': {'range': [None, 100]},
                       'bar': {'color': "red"},
                       'steps': [
                           {'range': [0, 5], 'color': "lightgreen"},
                           {'range': [5, 15], 'color': "yellow"},
                           {'range': [15, 100], 'color': "orange"}],
                       'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 15}}
            ))
            st.plotly_chart(fig_churn, use_container_width=True)
        
        st.subheader("Churn Details")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Users (Last Month)", format_metric(safe_get(churn_rate, 'total_users_month_ago'), '{:.0f}'))
        col2.metric("Active Users", format_metric(safe_get(churn_rate, 'active_users'), '{:.0f}'))
        col3.metric("Churned Users", format_metric(safe_get(churn_rate, 'churned_users'), '{:.0f}'))
    else:
        st.warning("Churn rate data is not available.")

def render_user_journey(user_journey):
    st.header("User Journey")
    if user_journey:
        journey_df = pd.DataFrame(user_journey)
        journey_df['timestamp'] = pd.to_datetime(journey_df['timestamp'])
        journey_df = journey_df.sort_values('timestamp')
        
        fig_journey = px.timeline(journey_df, x_start="timestamp", x_end="timestamp", y="event_type", color="event_type",
                                  hover_data=["event_data"])
        fig_journey.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_journey, use_container_width=True)
    else:
        st.warning("User journey data is not available.")

def main():
    st.set_page_config(page_title="Analytics Dashboard", layout="wide")
    render_analytics_page()

if __name__ == "__main__":
    main()