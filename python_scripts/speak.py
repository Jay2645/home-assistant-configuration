message = data.get('message')
entity_id = data.get('entity_id', 'group.broadcast_speakers')
should_michelle_hear = data.get('bug_michelle', True)

speakers_off = hass.states.is_state("binary_sensor.speakers_playing", "off")
michelle_not_home = not hass.states.is_state("person.michelle_kimsey_bailey", "home")

now = datetime.datetime.now().time()
latest = datetime.time(3,0,0)
earliest = datetime.time(12,0,0)

if message is not None:
    # Broadcast if the speakers are off and:
    # - Michelle isn't home OR
    # - Michelle is home and it's within a decent time AND Michelle can hear it

    if speakers_off and (michelle_not_home or ((now <= latest or now >= earliest) and should_michelle_hear)):
        service_data = {'entity_id': entity_id, 'message': message }
        hass.services.call('tts', 'google_translate_say', service_data, True)
    else:
        service_data = {'message':"Unable to broadcast: \"" + message + "\""}
        hass.services.call('notify', 'push_hass', service_data, True)