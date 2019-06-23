message = data.get('message')

if message is not None:
    entity_id = data.get('entity_id', 'group.broadcast_speakers')
    should_michelle_hear = data.get('bug_michelle', True)
    also_push_notify = data.get('push_notification', False)

    speakers_off = hass.states.is_state("binary_sensor.speakers_playing", "off")
    
    should_broadcast = speakers_off
    if should_broadcast:
        # Check if Michelle is home
        michelle_home = hass.states.is_state("person.michelle_kimsey_bailey", "home")
        if michelle_home:
            # Michelle is home, check if she should hear
            should_broadcast = should_michelle_hear
            if should_broadcast:
                # Michelle can hear this, make sure we're not annoying her too much
                now = datetime.datetime.now().time()
                latest = datetime.time(2,0,0)
                earliest = datetime.time(12,0,0)
                should_broadcast = now <= latest or now >= earliest

    if should_broadcast:
        service_data = {'entity_id': entity_id, 'message': message }
        hass.services.call('tts', 'google_translate_say', service_data, True)
    
    # If broadcasting failed or we should also do a push notification, do that
    if also_push_notify or not should_broadcast:
        service_data = {'message': message}
        hass.services.call('notify', 'push_hass', service_data, True)