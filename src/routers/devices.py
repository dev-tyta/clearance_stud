from fastapi import APIRouter, HTTPException, Depends, status, Header
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session as SQLAlchemySessionType
from typing import Dict, Any, List, Optional # Added List for _format_clearance_for_scan_response

from src import crud, models
from src.database import get_db
from src.auth import get_verified_device # Returns ORM Device model

router = APIRouter(
    prefix="/api", # Keep common prefix or change to /api/devices if preferred
    tags=["devices"],
)

@router.post("/devices/register", response_model=models.DeviceResponse)
async def register_device_endpoint( # Async endpoint
    device_data: models.DeviceRegister, # Pydantic model from ESP32
    db: SQLAlchemySessionType = Depends(get_db)
):
    """
    ESP32 devices self-register or re-register. Uses ORM.
    """
    # crud.register_device_esp is sync, call with run_in_threadpool
    try:
        registered_device_orm = await run_in_threadpool(crud.register_device_esp, db, device_data)
    except HTTPException as e: # Catch HTTPExceptions raised by CRUD (e.g., device already exists)
        raise e
    return registered_device_orm # Pydantic DeviceResponse converts from ORM model


# Helper for formatting scan response (moved to be more specific to this router's needs)
async def _format_clearance_for_device_scan(
    db: SQLAlchemySessionType, # Pass db session for sync crud calls
    student_orm: models.Student # Expect Student ORM model
) -> models.ClearanceDetail:
    """Helper to format clearance details for the /scan endpoint response using ORM."""
    
    # crud.get_clearance_statuses_by_student_id is sync, needs run_in_threadpool
    statuses_orm_list = await run_in_threadpool(crud.get_clearance_statuses_by_student_id, db, student_orm.student_id)
    
    clearance_items_models: List[models.ClearanceStatusItem] = []
    overall_status_val = models.OverallClearanceStatusEnum.COMPLETED

    if not statuses_orm_list:
        overall_status_val = models.OverallClearanceStatusEnum.PENDING
    
    for status_orm in statuses_orm_list:
        item = models.ClearanceStatusItem(
            department=status_orm.department, # Already enum from ORM
            status=status_orm.status,       # Already enum from ORM
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

@router.post("/scan", response_model=models.ClearanceDetail)
async def scan_tag_endpoint( # Async endpoint
    scan_data: models.TagScan, # Contains device_id (hardware_id) and tag_id
    verified_device_orm: models.Device = Depends(get_verified_device), # Returns ORM Device model
    db: SQLAlchemySessionType = Depends(get_db)
):
    """
    Device scans a tag. Verifies device, logs scan, gets student clearance. ORM-based.
    """
    if verified_device_orm.device_id != scan_data.device_id: # Compare hardware IDs
        # This might indicate a misconfiguration or an attempt to spoof.
        # Log this with verified_device_orm.id and scan_data.device_id
        await run_in_threadpool(
            crud.create_device_log, db, verified_device_orm.id, "scan_error_device_id_mismatch",
            scanned_tag_id=scan_data.tag_id, actual_device_id_str=scan_data.device_id
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device identity mismatch. API key valid, but payload device_id differs."
        )

    device_pk = verified_device_orm.id
    device_hw_id = verified_device_orm.device_id # ESP32's hardware ID (string)

    # Update last seen (sync crud)
    await run_in_threadpool(crud.update_device_last_seen, db, device_pk)
    
    # Check if tag belongs to a student
    student_orm = await run_in_threadpool(crud.get_student_by_tag_id, db, scan_data.tag_id)

    if student_orm:
        await run_in_threadpool(
            crud.create_device_log, db, device_pk, "scan_student_clearance",
            scanned_tag_id=scan_data.tag_id, user_type=models.UserRole.STUDENT.value, actual_device_id_str=device_hw_id
        )
        return await _format_clearance_for_device_scan(db, student_orm)
    else:
        # Check if tag belongs to staff/admin (not for clearance check, but for logging)
        user_orm = await run_in_threadpool(crud.get_user_by_tag_id, db, scan_data.tag_id)
        user_type_log = models.UserRole.ADMIN.value if user_orm and user_orm.role == models.UserRole.ADMIN else \
                        models.UserRole.STAFF.value if user_orm and user_orm.role == models.UserRole.STAFF else \
                        "unknown_user_tag"
        
        await run_in_threadpool(
             crud.create_device_log, db, device_pk, f"scan_failed_not_student_tag ({user_type_log})",
             scanned_tag_id=scan_data.tag_id, user_type=user_type_log, actual_device_id_str=device_hw_id
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag does not belong to a registered student for clearance check.")


@router.post("/devices/submit-scanned-tag", response_model=Dict) # Return a success message dict
async def submit_scanned_tag_endpoint( # Async endpoint
    payload: models.ScannedTagSubmit, # Contains scanned_tag_id
    verified_device_orm: models.Device = Depends(get_verified_device), # Returns ORM Device model
    db: SQLAlchemySessionType = Depends(get_db)
):
    """
    Device submits a scanned tag to complete a pending link. ORM-based.
    """
    device_pk = verified_device_orm.id
    device_hw_id = verified_device_orm.device_id # ESP32's hardware ID (string)

    # crud.get_active_pending_tag_link_by_device_pk is sync
    pending_link_orm = await run_in_threadpool(crud.get_active_pending_tag_link_by_device_pk, db, device_pk)

    if not pending_link_orm:
        await run_in_threadpool(
            crud.create_device_log, db, device_pk, "submit_tag_failed_no_pending",
            scanned_tag_id=payload.scanned_tag_id, actual_device_id_str=device_hw_id
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active tag linking process for this device.")

    # Check tag uniqueness (crud.check_tag_id_globally_unique_for_target is sync and raises HTTPException)
    try:
        await run_in_threadpool(
            crud.check_tag_id_globally_unique_for_target,
            db,
            payload.scanned_tag_id,
            pending_link_orm.target_user_type, # Pass the TargetUserType enum
            # PK of the target entity (student.id or user.id) is NOT known here yet.
            # The check_tag_id_globally_unique_for_target needs to be careful if target_pk is None
            # or fetch the target's PK if the identifier is unique (student_id/username).
            # For now, pass None for target_pk, meaning it checks against ALL existing.
            # This is safer. If target was already assigned this tag, it should have been caught
            # during prepare_tag_link.
            None 
        )
    except HTTPException as e_tag_conflict: # Specifically catch tag conflict from the check
        await run_in_threadpool(crud.delete_pending_tag_link, db, pending_link_orm.id) # Cancel link
        await run_in_threadpool(
            crud.create_device_log, db, device_pk, "submit_tag_failed_tag_conflict",
            scanned_tag_id=payload.scanned_tag_id, actual_device_id_str=device_hw_id
        )
        raise e_tag_conflict # Re-raise the 409

    linked_identifier_val: Optional[str] = None
    try:
        if pending_link_orm.target_user_type == models.TargetUserType.STUDENT:
            # crud.update_student_tag_id is sync
            updated_student_orm = await run_in_threadpool(
                crud.update_student_tag_id, db, pending_link_orm.target_identifier, payload.scanned_tag_id
            )
            linked_identifier_val = updated_student_orm.student_id
        elif pending_link_orm.target_user_type == models.TargetUserType.STAFF_ADMIN:
            # crud.update_user_tag_id is sync
            updated_user_orm = await run_in_threadpool(
                crud.update_user_tag_id, db, pending_link_orm.target_identifier, payload.scanned_tag_id
            )
            linked_identifier_val = updated_user_orm.username
        
        # Delete the processed pending link (sync crud)
        await run_in_threadpool(crud.delete_pending_tag_link, db, pending_link_orm.id)
        
        # Log success (sync crud)
        await run_in_threadpool(crud.update_device_last_seen, db, device_pk)
        await run_in_threadpool(
            crud.create_device_log, db, device_pk,
            f"tag_linked_to_{pending_link_orm.target_user_type.value}:{linked_identifier_val}",
            scanned_tag_id=payload.scanned_tag_id, actual_device_id_str=device_hw_id
        )

        return {
            "message": f"Tag ID '{payload.scanned_tag_id}' successfully linked to {pending_link_orm.target_user_type.value} '{linked_identifier_val}'.",
            "device_id": device_hw_id,
            "tag_id": payload.scanned_tag_id,
        }
    except HTTPException as e_update: # Catch errors from update_..._tag_id
        # If update fails (e.g. target not found, though checked in prepare), log and raise
        await run_in_threadpool(
            crud.create_device_log, db, device_pk, f"submit_tag_failed_update_error: {e_update.detail}",
            scanned_tag_id=payload.scanned_tag_id, actual_device_id_str=device_hw_id
        )
        # Consider if pending link should be deleted on update failure.
        # It might be better to leave it for investigation if it wasn't a tag conflict.
        raise e_update
    except Exception as e_generic:
        print(f"Unexpected error during submit_scanned_tag: {e_generic}")
        await run_in_threadpool(
            crud.create_device_log, db, device_pk, "submit_tag_failed_unexpected_error",
            scanned_tag_id=payload.scanned_tag_id, actual_device_id_str=device_hw_id
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred linking the tag.")

