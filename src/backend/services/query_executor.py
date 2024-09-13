from src.backend.services.azure_devops_service import AzureDevOpsService
from src.backend.models.models import DevOpsCache
from src.backend.db.session import SessionLocal
from datetime import datetime, timedelta

class QueryExecutor:
    def __init__(self, azure_devops_service: AzureDevOpsService):
        self.azure_devops_service = azure_devops_service

    def execute_query(self, category: str, entities: dict, query: str):
        if category == "velocity":
            return self._get_team_velocity(entities["project"], entities["team"])
        elif category == "work_items":
            return self._get_work_items(entities["project"], entities["team"], query)
        else:
            return f"Unsupported query category: {category}"

    def _get_team_velocity(self, project: str, team: str):
        cache_key = f"velocity_{project}_{team}"
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data

        velocity = self.azure_devops_service.get_team_velocity(project, team)
        self._store_in_cache(cache_key, velocity, timedelta(hours=24))
        return velocity

    def _get_work_items(self, project: str, team: str, query: str):
        work_items = self.azure_devops_service.get_work_items(project, team, query)
        return work_items

    def _get_from_cache(self, key: str):
        db = SessionLocal()
        try:
            cached_item = db.query(DevOpsCache).filter(
                DevOpsCache.cache_key == key,
                DevOpsCache.organization_id == self.azure_devops_service.organization_id,
                DevOpsCache.expires_at > datetime.utcnow()
            ).first()
            return cached_item.cache_value if cached_item else None
        finally:
            db.close()

    def _store_in_cache(self, key: str, value: any, ttl: timedelta):
        db = SessionLocal()
        try:
            db.add(DevOpsCache(
                cache_key=key,
                cache_value=value,
                expires_at=datetime.utcnow() + ttl,
                organization_id=self.azure_devops_service.organization_id
            ))
            db.commit()
        finally:
            db.close()