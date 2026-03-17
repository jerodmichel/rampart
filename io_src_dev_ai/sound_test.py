

# ░██████╗░█████╗░██╗░░░██╗███╗░░██╗██████╗░████████╗███████╗░██████╗████████╗
# ██╔════╝██╔══██╗██║░░░██║████╗░██║██╔══██╗╚══██╔══╝██╔════╝██╔════╝╚══██╔══╝
# ╚█████╗░██║░░██║██║░░░██║██╔██╗██║██║░░██║░░░██║░░░█████╗░░╚█████╗░░░░██║░░░
# ░╚═══██╗██║░░██║██║░░░██║██║╚████║██║░░██║░░░██║░░░██╔══╝░░░╚═══██╗░░░██║░░░
# ██████╔╝╚█████╔╝╚██████╔╝██║░╚███║██████╔╝░░░██║░░░███████╗██████╔╝░░░██║░░░
# ╚═════╝░░╚════╝░░╚═════╝░╚═╝░░╚══╝╚═════╝░░░░╚═╝░░░╚══════╝╚═════╝░░░░╚═╝░░░

import pygame
import os
import time

def test_playback():
    pygame.init()
    
    # try different audio configurations
    configs = [
        {'driver': 'alsa', 'device': 'default'},  # Linux default
        {'driver': 'pulse', 'device': 'default'}, # Linux PulseAudio
        {'driver': 'directsound', 'device': None}, # Windows
        {'driver': 'coreaudio', 'device': None}    # MacOS
    ]
    
    for cfg in configs:
        try:
            # set environment variables
            if cfg['driver']:
                os.environ['SDL_AUDIODRIVER'] = cfg['driver']
            if cfg['device']:
                os.environ['AUDIODEV'] = cfg['device']
            
            # reinitialize mixer
            pygame.mixer.quit()
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
            
            print(f"\nTrying config: {cfg}")
            print(f"Current driver: {pygame.mixer.get_driver()}")
            
            # load and play sound
            sound = pygame.mixer.Sound('assets/sounds/thunder_strike.wav')
            channel = sound.play()
            
            if channel:
                print("Playing sound...")
                while channel.get_busy():
                    pygame.time.delay(100)
                print("Playback finished successfully!")
                return True
            else:
                print("Playback failed (no channel available)")
                
        except Exception as e:
            print(f"Error: {str(e)}")
    
    return False

if not test_playback():
    print("\nAll playback attempts failed!")

pygame.quit()