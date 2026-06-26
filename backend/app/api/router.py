from fastapi import APIRouter

from app.api import admin_users, attachments, audit_logs, auth, daily_logs, daily_reports, experiment_records, experiments, health, projects, reagents, testing, users


api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(admin_users.router, prefix="/admin", tags=["admin"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["audit_logs"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(experiments.router, prefix="/experiments", tags=["experiments"])
api_router.include_router(experiment_records.router, prefix="/experiment-records", tags=["experiment_records"])
api_router.include_router(daily_logs.router, prefix="/daily-logs", tags=["daily_logs"])
api_router.include_router(daily_reports.router, prefix="/daily-reports", tags=["daily_reports"])
api_router.include_router(attachments.router, prefix="/attachments", tags=["attachments"])
api_router.include_router(reagents.reagents_router, prefix="/reagents", tags=["reagents"])
api_router.include_router(reagents.reagent_lots_router, prefix="/reagent-lots", tags=["reagent_lots"])
api_router.include_router(reagents.inventory_txns_router, prefix="/inventory-transactions", tags=["inventory_transactions"])
api_router.include_router(testing.samples_router, prefix="/samples", tags=["samples"])
api_router.include_router(testing.methods_router, prefix="/test-methods", tags=["test_methods"])
api_router.include_router(testing.tasks_router, prefix="/test-tasks", tags=["test_tasks"])
api_router.include_router(testing.results_router, prefix="/test-results", tags=["test_results"])
