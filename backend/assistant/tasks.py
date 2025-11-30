from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import AgendaEvent, PushSubscription
from .services.push_notification_service import send_push_notification


@shared_task
def check_upcoming_events():
    """
    Check for events starting in the next 15 minutes and send push notifications.
    This task runs every minute via Celery Beat.
    """
    now = timezone.now()
    # Check events starting between now and 15 minutes from now
    time_window_start = now
    time_window_end = now + timedelta(minutes=15)
    
    # Find events that start in this window and haven't been notified yet
    upcoming_events = AgendaEvent.objects.filter(
        start_datetime__gte=time_window_start,
        start_datetime__lte=time_window_end,
    ).select_related('user')
    
    notified_events = []
    
    for event in upcoming_events:
        # Get all push subscriptions for this user
        subscriptions = PushSubscription.objects.filter(user=event.user)
        
        if not subscriptions.exists():
            continue
        
        # Format the notification message
        if event.all_day:
            time_str = "All day"
        else:
            time_str = event.start_datetime.strftime("%H:%M")
        
        message = f"Evento a chegar: {event.title}"
        if event.location:
            message += f" em {event.location}"
        message += f" às {time_str}"
        
        # Send notification to all user's subscriptions
        for subscription in subscriptions:
            try:
                send_push_notification(
                    subscription=subscription,
                    title="Evento na Agenda",
                    body=message,
                    data={
                        'type': 'agenda_event',
                        'event_id': event.id,
                        'title': event.title,
                    }
                )
            except Exception as e:
                # Log error but continue with other subscriptions
                print(f"Error sending push notification: {e}")
        
        notified_events.append(event.id)
    
    return {
        'checked_events': upcoming_events.count(),
        'notified_events': len(notified_events),
        'event_ids': notified_events
    }

