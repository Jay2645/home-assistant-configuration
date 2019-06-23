message = data.get('message')
entity_id = data.get('entity_id', 'group.broadcast_speakers')

speakers_off = hass.states.is_state("binary_sensor.speakers_playing", "off")

now = datetime.datetime.now().time()
latest = datetime.time(3,0,0)
earliest = datetime.time(12,0,0)

if message is not None:
    if (now <= latest or now >= earliest) and speakers_off:
        service_data = {'entity_id': entity_id, 'message': message }
        hass.services.call('tts', 'google_translate_say', service_data, True)
    else:
        service_data = {'message':"Unable to broadcast: \"" + message + "\""}
        hass.services.call('notify', 'push_hass', service_data, True)