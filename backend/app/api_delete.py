
@router.delete("/events/{event_id}", status_code=204)
def delete_event(
    event_id: int, 
    db: Session = Depends(get_db),
    # Optional: User Auth Dependency (e.g. Depends(verify_admin))
    # current_user: User = Depends(get_current_active_admin)
):
    """
    Delete an event (admin only).
    Also updates associated articles to 'rejected' status so they don't reappear.
    """
    ev = db.query(Event).filter(Event.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
        
    # Mark all associated articles as Rejected/Hidden
    # We set status to 'rejected' so they are not re-clustered.
    # We also unlink them from the event (event_id = NULL) to ensure data integrity before deleting the event row.
    db.query(Article).filter(Article.event_id == event_id).update(
        {"status": "rejected", "event_id": None}, 
        synchronize_session=False
    )
    
    # Delete the event
    db.delete(ev)
    db.commit()
    
    return
