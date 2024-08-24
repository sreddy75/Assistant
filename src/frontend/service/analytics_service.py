import json
from datetime import datetime
from sqlalchemy import create_engine, Table, Column, Integer, String, TIMESTAMP, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

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

analytics_service = AnalyticsService(os.getenv("DB_URL"))