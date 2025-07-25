from typing import List, Dict, Any
from sqlalchemy.orm import Session as SQLAlchemySessionType
from fastapi.concurrency import run_in_threadpool

from src import crud, models

async def format_student_clearance_details(
    db: SQLAlchemySessionType,
    student_orm: models.Student
) -> models.ClearanceDetail:
    """
    Formats clearance details for a student.
    
    Args:
        db (SQLAlchemySessionType): Database session.
        student_orm (models.Student): ORM model of the student.
    
    Returns:
        models.ClearanceDetail: Formatted clearance details.
    """
    statuses_orm_list = await run_in_threadpool(crud.get_clearance_statuses_by_student_id, db, student_orm.student_id)
    
    clearance_items_models: List[models.ClearanceStatusItem] = []
    overall_status_val = models.OverallClearanceStatusEnum.COMPLETED

    
    if not statuses_orm_list:
        overall_status_val = models.OverallClearanceStatusEnum.PENDING
    
    for status_orm in statuses_orm_list:
        item = models.ClearanceStatusItem(
            department=status_orm.department,
            status=status_orm.status,
            remarks=status_orm.remarks,
            updated_at=status_orm.updated_at
        )
        clearance_items_models.append(item)
        if item.status != models.ClearanceStatusEnum.COMPLETED:
            overall_status_val = models.OverallClearanceStatusEnum.PENDING
            
    if not statuses_orm_list and overall_status_val == models.OverallClearanceStatusEnum.COMPLETED:
         overall_status_val = models.OverallClearanceStatusEnum.PENDING

    return models.ClearanceDetail(
        student_id=student_orm.student_id,
        name=student_orm.name,
        department=student_orm.department,
        clearance_items=clearance_items_models,
        overall_status=overall_status_val
    )

