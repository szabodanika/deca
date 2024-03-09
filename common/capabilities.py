
ALL_CAPABILITIES = [
    
    # these are mostly for resource nodes
    
        # capability to switch something on and off
        # state is a boolean ('true' or 'false')
        'actuator_switch',
        # capability to read value (e.g. temperature sensor)
        'sensor_read',

    # below are mostly for embodiment nodes

        # can play audio
        'audio_out',
        # can display text
        'text_out',
        # can read text in from user
        'text_in',
        # can display images
        'image_out'
        # speech recognition
        'speech_in'
]