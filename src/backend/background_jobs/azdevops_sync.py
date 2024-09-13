from src.backend.services.azure_devops_service import AzureDevOpsService
from src.backend.models.models import AzureDevOpsConfig, DevOpsProject, DevOpsTeam, WorkItemType
from src.backend.db.session import SessionLocal

def sync_azure_devops_metadata():
    db = SessionLocal()
    configs = db.query(AzureDevOpsConfig).all()
    for config in configs:
        service = AzureDevOpsService(config.organization_url, config.personal_access_token)
        projects = service.get_projects()
        for project in projects:
            db_project = DevOpsProject(
                organization_id=config.organization_id,
                project_id=project.id,
                name=project.name,
                description=project.description
            )
            db.add(db_project)
            db.flush()

            teams = service.get_teams(project.id)
            for team in teams:
                db_team = DevOpsTeam(
                    project_id=db_project.id,
                    team_id=team.id,
                    name=team.name
                )
                db.add(db_team)

            work_item_types = service.get_work_item_types(project.id)
            for wit in work_item_types:
                db_wit = WorkItemType(
                    project_id=db_project.id,
                    name=wit.name,
                    fields=wit.fields
                )
                db.add(db_wit)

    db.commit()
    db.close()