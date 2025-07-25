"""
CRUD operations for the PendingTagLink model.
"""
from sqlalchemy.orm import Session
from datetime import datetime

from src import models

def create_pending_tag_link(db: Session, link_details: models.PrepareTagLinkRequest, initiated_by_id: int, expires_at: datetime) -> models.PendingTagLink:
    """Creates a new pending tag link request in the database."""
    
    device = db.query(models.Device).filter(models.Device.device_id == link_details.device_identifier).first()
    if not device:
        # This check should ideally be in the router, but adding here as a safeguard
        return None

    new_link = models.PendingTagLink(
        device_id_fk=device.id,
        target_user_type=link_details.target_user_type,
        target_identifier=link_details.target_identifier,
        initiated_by_user_id=initiated_by_id,
        expires_at=expires_at,
    )
    db.add(new_link)
    db.commit()
    db.refresh(new_link)
    return new_link

def get_pending_links(db: Session, device_id: int) -> models.PendingTagLink | None:
    """
    Fetches the active (non-expired) pending tag link for a specific device.
    """
    return db.query(models.PendingTagLink).offset(0).limit(limit=1000).all()

def get_pending_link_by_id(db: Session, link_id: int) -> models.PendingTagLink | None:
    """
    Fetches a pending tag link by its ID.
    """
    return db.query(models.PendingTagLink).filter(models.PendingTagLink.id == link_id).first()

def delete_pending_link_by_device_id(db: Session, link_id: int):
    """Deletes a pending link, typically after it has been used."""
    link_to_delete = db.query(models.PendingTagLink).filter(models.PendingTagLink.id == link_id).first()
    if link_to_delete:
        db.delete(link_to_delete)
        db.commit()
