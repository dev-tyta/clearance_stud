from sqlmodel import Session, select
from typing import Optional, Union

from src.models import RFIDTag, User, Student, TagLink

def link_tag(db: Session, link_data: TagLink) -> Optional[RFIDTag]:
    """
    Links an RFID tag to a user or student.

    This function performs several crucial validation checks:
    1. Ensures the tag is not already linked to another person.
    2. Ensures the target user/student does not already have a tag.
    3. Ensures either a matric_no or username is provided.

    Returns the new RFIDTag object on success, None on failure.
    The calling router is responsible for raising the appropriate HTTP exception.
    """
    # 1. Check if the tag is already in use
    existing_tag = db.exec(select(RFIDTag).where(RFIDTag.tag_id == link_data.tag_id)).first()
    if existing_tag:
        return None # Failure: Tag already exists

    target_person: Optional[Union[User, Student]] = None
    
    if link_data.matric_no:
        target_person = db.exec(select(Student).where(Student.matric_no == link_data.matric_no)).first()
    elif link_data.username:
        target_person = db.exec(select(User).where(User.username == link_data.username)).first()
    else:
        return None # Failure: No identifier provided

    if not target_person:
        return None # Failure: Target person not found
        
    # 2. Check if the person already has a tag linked
    if target_person.rfid_tag:
        return None # Failure: Person already has a tag

    # Create and link the new tag
    new_tag = RFIDTag(tag_id=link_data.tag_id)
    if isinstance(target_person, Student):
        new_tag.student_id = target_person.id
    else:
        new_tag.user_id = target_person.id
        
    db.add(new_tag)
    db.commit()
    db.refresh(new_tag)
    
    return new_tag

def unlink_tag(db: Session, tag_id: str) -> Optional[RFIDTag]:
    """
    Unlinks an RFID tag, making it available for re-assignment.
    Returns the deleted tag object on success, None if the tag doesn't exist.
    """
    tag_to_delete = db.exec(select(RFIDTag).where(RFIDTag.tag_id == tag_id)).first()
    
    if not tag_to_delete:
        return None # Tag not found
        
    db.delete(tag_to_delete)
    db.commit()
    
    return tag_to_delete
