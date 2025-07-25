"""
Router for all CRUD operations related to students.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session as SQLAlchemySessionType
from typing import List

from src import crud, models
from src.auth import get_current_active_admin_user_from_token
from src.database import get_db
from src.utils import format_student_clearance_details

router = APIRouter(
    prefix="/api/students",
    tags=["students"],
    )

@router.post("/", response_model=models.StudentResponse, status_code=status.HTTP_201_CREATED)
async def create_student_endpoint(
    student_data: models.StudentCreate,
    db: SQLAlchemySessionType = Depends(get_db),
):
    """Admin: Create a new student."""
    try:
        created_student_orm = await run_in_threadpool(crud.create_student, db, student_data)
        return created_student_orm
    except HTTPException as e:
        raise e

@router.get("/", response_model=List[models.StudentResponse])
async def get_students_endpoint(
    skip: int = 0,
    limit: int = 100,
    db: SQLAlchemySessionType = Depends(get_db),
):
    """Admin: Get a list of all students."""
    students_orm_list = await run_in_threadpool(crud.get_all_students, db, skip, limit)
    return students_orm_list

@router.get("/{student_id_str}", response_model=models.ClearanceDetail)
async def get_student_clearance_endpoint(
    student_id_str: str,
    db: SQLAlchemySessionType = Depends(get_db),
):
    """Admin: Get detailed clearance status for a specific student."""
    student_orm = await run_in_threadpool(crud.get_student_by_student_id, db, student_id_str)
    if not student_orm:
        raise HTTPException(status_code=404, detail="Student not found")
    return await format_student_clearance_details(db, student_orm)

@router.delete("/{student_id_str}", status_code=status.HTTP_200_OK, response_model=dict)
async def delete_student_endpoint(
    student_id_str: str,
    db: SQLAlchemySessionType = Depends(get_db),
):
    """
    Admin: Permanently deletes a student and all associated records.
    """
    try:
        deleted_student = await run_in_threadpool(crud.delete_student, db, student_id_str)
        return {"message": "Student deleted successfully", "student_id": deleted_student.student_id}
    except HTTPException as e:
        raise e
