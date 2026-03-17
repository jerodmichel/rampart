#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Mar 14 01:36:26 2026

@author: stereo
"""

import pygame
import sys
import subprocess
import os
import time


class Launcher:
    def __init__(self):
        os.environ['SDL_VIDEO_CENTERED'] = '1'
        
        import platform
        if platform.system() == "Windows":
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        
        pygame.init()
        
        # splash art
        self.bg_path = "rampart_bg.png"
        try:
            self.bg_image = pygame.image.load(self.bg_path)
            self.width = self.bg_image.get_width()
            self.height = self.bg_image.get_height()
        except Exception as e:
            print(f"Could not load background image: {e}")
            self.width, self.height = 800, 600 # fallback sizes
            self.bg_image = None
            
        self.screen = pygame.display.set_mode((self.width, self.height))
        
        # adjust size here
        pygame.display.set_caption("Rampart -- Main Menu")
        self.font = pygame.font.Font("fonts/cinzel/Cinzel-Black.ttf", 26)
        self.about_font = pygame.font.SysFont("timesnewroman", 22)
        
        # about
        self.show_about = False
        
        self.music_path = "alexgrohl-metal.mp3"
        try:
            pygame.mixer.music.load(self.music_path)
            pygame.mixer.music.play(-1) # -1 loops it infinitely
        except Exception as e:
            print(f"Could not load music: {e}")
            
    def draw_about_overlay(self):
        # 1. dim the background
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210)) 
        self.screen.blit(overlay, (0, 0))
    
        # 2. draw box
        box_w, box_h = 550, 550
        box_rect = pygame.Rect((self.width//2 - box_w//2), (self.height//2 - box_h//2), box_w, box_h)
        pygame.draw.rect(self.screen, (30, 30, 35), box_rect, border_radius=15)
        pygame.draw.rect(self.screen, (180, 180, 180), box_rect, 2, border_radius=15)
    
        # 3. text content
        lines = [
            ("RAMPART", True),              
            ("", False),
            ("A strategic hybrid of chess and", False),
            ("cardplay where players battle across", False),
            ("a rampart barrier using tactical", False),
            ("movement and card-based casting.", False),
            ("", False),
            ("Credits:", True),
            ("", False),
            ("Lead Dev: Jerod Michel", False),
            ("Support Dev: Jordan Michel, Mac McMorran", False),
            ("Splash Art/Other Art: Leland Stuebig/Billy Hill", False),
            ("Music: Alex Grohl", False),
            ("", False),
            ("( Click anywhere to close )", False)
        ]
        
        # margin
        left_margin = box_rect.left + 30
        
        for i, (text, is_title) in enumerate(lines):
            # fonts
            current_font = self.font if is_title else self.about_font
            
            # colors
            if i == 14: 
                color = (255, 0, 0) # Red
            else:
                color = (125, 249, 255) if is_title else (220, 220, 220)
            
            txt_surf = current_font.render(text, True, color)
            
            # alignment logic
            if i < 9 or i == 14:
                txt_rect = txt_surf.get_rect(centerx=self.width//2, top=box_rect.top + 30 + (i * 28))
            else:
                txt_rect = txt_surf.get_rect(left=left_margin, top=box_rect.top + 30 + (i * 28))
                
            self.screen.blit(txt_surf, txt_rect)

    def mainloop(self):
        
        while True:
            mouse_pos = pygame.mouse.get_pos()
            
            # 1. Draw Background
            if self.bg_image:
                self.screen.blit(self.bg_image, (0, 0))
            else:
                self.screen.fill((20, 20, 25))
            
            # 2. Setup Buttons (Automatic Width)
            button_data = [
                ("Play vs AI", "ai"),
                ("Play Multiplayer", "multi"),
                ("About", "about")
            ]
            
            button_rects = {}
            padding_x, padding_y = 25, 10
            current_x = 40 # Start from left (or calculate for right)
            
            # Calculate total width to align group to the bottom right
            total_width = 0
            rendered_buttons = []
            for text, tag in button_data:
                surf = self.font.render(text, True, (20, 20, 10))
                w, h = surf.get_width() + (padding_x * 2), surf.get_height() + (padding_y * 2)
                rendered_buttons.append((surf, w, h, tag))
                total_width += w + 20 # 20 is gap

            # Draw buttons aligned to bottom right
            start_x = self.width - total_width - 20
            btn_y = self.height - 70

            for surf, w, h, tag in rendered_buttons:
                rect = pygame.Rect(start_x, btn_y, w, h)
                button_rects[tag] = rect
                
                # Hover color logic
                color = (150, 150, 150) if rect.collidepoint(mouse_pos) else (240, 240, 245)
                pygame.draw.rect(self.screen, color, rect, border_radius=10)
                
                # Center text in the dynamic rect
                txt_rect = surf.get_rect(center=rect.center)
                self.screen.blit(surf, txt_rect)
                start_x += w + 20 # Move x for next button

            # 3. Draw Overlay if active
            if self.show_about:
                self.draw_about_overlay()
            
            # 4. Event Handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                    
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.show_about:
                        self.show_about = False # Close overlay on click
                    else:
                        if button_rects["ai"].collidepoint(mouse_pos):
                            self.launch_game("main.py", "io_src_dev_ai")
                        elif button_rects["multi"].collidepoint(mouse_pos):
                            self.launch_game("main.py", "io_src_dev")
                        elif button_rects["about"].collidepoint(mouse_pos):
                            self.show_about = True
                            
            pygame.display.update()
            
    def launch_game(self, script_name, folder_name):
        
        pygame.quit()
        
        try:
            if getattr(sys, 'frozen', False):
                target_exe = script_name.replace('.py', '.exe')
                full_exe_path = os.path.abspath(os.path.join(folder_name, target_exe))
                subprocess.run([full_exe_path], cwd=folder_name)
            else:
                subprocess.run([sys.executable, script_name], cwd=folder_name)
        except Exception as e:
            print(f"Failed to launch {script_name}: {e}")
            time.sleep(1.0)
            
        os.environ['SDL_VIDEO_CENTERED'] = '1'
        pygame.init()
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Rampart -- Main Menu")
        self.font = pygame.font.Font("fonts/cinzel/Cinzel-Black.ttf", 28)
        self.about_font = pygame.font.SysFont("timesnewroman", 22) # <-- ADD THIS LINE
        
        # reload image
        if self.bg_path:
            try:
                self.bg_image = pygame.image.load(self.bg_path)
            except:
                pass
            
        if hasattr(self, 'music_path'):
            try:
                pygame.mixer.music.load(self.music_path)
                pygame.mixer.music.play(-1)
            except:
                pass
        
        
if __name__ == "__main__":
    launcher = Launcher()
    launcher.mainloop()
        
        
        
        
        