import pygame
import os
import sys
import math
import random

# Initialize pygame
pygame.init()

# Initialize pygame mixer for sounds
pygame.mixer.init()

# Define folder paths
SPRITE_FOLDER = "sprites"
SOUND_FOLDER = "sounds"

# Helper function to load assets from the correct folders
def get_asset_path(filename, folder):
    """Return the correct path for an asset file, checking multiple possible locations."""
    # Try direct path in the specified folder
    direct_path = os.path.join(folder, filename)
    if os.path.exists(direct_path):
        return direct_path
        
    # Try from script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, folder, filename)
    if os.path.exists(script_path):
        return script_path
        
    # Fallback to root directory
    fallback_path = os.path.join(script_dir, filename)
    if os.path.exists(fallback_path):
        return fallback_path
        
    # Return the direct path anyway (will fail, but with a clearer error)
    return direct_path

# Load sounds with better fallback
try:
    point_sound = pygame.mixer.Sound(get_asset_path('point.ogg', SOUND_FOLDER))
    # Set a short fadeout to ensure sound doesn't overlap
    point_sound.set_volume(0.7)
except (pygame.error, FileNotFoundError):
    try:
        point_sound = pygame.mixer.Sound(get_asset_path('point.wav', SOUND_FOLDER))  # Try WAV as fallback
    except (pygame.error, FileNotFoundError):
        print("Warning: Could not load point sound")
        point_sound = pygame.mixer.Sound(buffer=bytes(bytearray(16)))
        point_sound.set_volume(0)

try:
    hit_sound = pygame.mixer.Sound(get_asset_path('hit.wav', SOUND_FOLDER))
    hit_sound.set_volume(1.0)  # Full volume for hit sound
except (pygame.error, FileNotFoundError):
    try:
        hit_sound = pygame.mixer.Sound(get_asset_path('hit.ogg', SOUND_FOLDER))  # Try OGG as fallback
    except (pygame.error, FileNotFoundError):
        print("Warning: Could not load hit sound")
        hit_sound = pygame.mixer.Sound(buffer=bytes(bytearray(16)))
        hit_sound.set_volume(0)

try:
    die_sound = pygame.mixer.Sound(get_asset_path('die.wav', SOUND_FOLDER))
    die_sound.set_volume(1.0)  # Full volume for die sound
except (pygame.error, FileNotFoundError):
    print("Warning: Could not load die.wav")
    die_sound = pygame.mixer.Sound(buffer=bytes(bytearray(16)))
    die_sound.set_volume(0)

try:
    wing_sound = pygame.mixer.Sound(get_asset_path('wing.ogg', SOUND_FOLDER))
    wing_sound.set_volume(0.7)
except (pygame.error, FileNotFoundError):
    try:
        wing_sound = pygame.mixer.Sound(get_asset_path('wing.wav', SOUND_FOLDER))  # Try WAV as fallback
    except (pygame.error, FileNotFoundError):
        print("Warning: Could not load wing sound")
        wing_sound = pygame.mixer.Sound(buffer=bytes(bytearray(16)))
        wing_sound.set_volume(0)

# Prevent Android keyboard from showing
os.environ['SDL_ANDROID_HIDE_KEYBOARD'] = '1'

# For Android - explicitly tell SDL to use the full screen area including notification bar
os.environ['SDL_ANDROID_IMMERSIVE_MODE'] = '1'

# Get the screen size of the device (MUST be after setting environment variables)
info = pygame.display.Info()
screen_width = info.current_w
screen_height = info.current_h

# If the screen is too wide relative to its height, limit the width to 412 pixels
if screen_width / screen_height > 1.2:  # If aspect ratio is wider than 1.2:1
    screen_width = 412

# Set up the display with FULLSCREEN and SCALED flags for better Android compatibility
screen = pygame.display.set_mode((screen_width, screen_height), pygame.FULLSCREEN | pygame.SCALED)
pygame.display.set_caption('Flappy Bird')

# Variable to track which theme we're using (day/night)
is_night_theme = False

# Disable Android keyboard
pygame.key.set_repeat(0)  # Disable key repeat which can trigger keyboard

# Add game area variables after screen setup
game_area_height = int(screen_height * 0.78)  # 78% of screen height
game_area_y_offset = int(screen_height * 0.11)  # 11% from top to center the game area
game_area_rect = pygame.Rect(0, game_area_y_offset, screen_width, game_area_height)

# Declare a global gravity variable
gravitational_force = 5
bird_velocity = 0  # Initial vertical velocity of the bird
bird_angle = 0  # Current rotation angle of the bird
max_upward_angle = 45  # Maximum rotation when jumping (positive for clockwise)
max_downward_angle = -45  # Maximum rotation when falling (negative for anticlockwise)
rotation_speed = 3  # How quickly the bird rotates
downward_rotation_speed = 10  # How quickly the bird rotates downward - adjustable

# Variables to ensure sounds only play once
die_sound_played = False
passed_pipe_ids = set()  # Store IDs of pipes we've played sounds for

# Variables to track passed pipes
passed_pipe_positions = set()  # Store positions of pipes we've already counted
screen_center_x = screen_width // 2  # Center of the screen

# Load game over image
try:
    gameover_img = pygame.image.load(get_asset_path('gameover.png', SPRITE_FOLDER))
except (pygame.error, FileNotFoundError):
    print("Warning: Could not load gameover.png")
    # Create a dummy surface
    gameover_img = pygame.Surface((300, 100))
    gameover_img.fill((255, 0, 0))
    font = pygame.font.SysFont(None, 40)
    text = font.render("GAME OVER", True, (255, 255, 255))
    gameover_img.blit(text, (75, 35))
        
# Scale the game over image
gameover_width = int(screen_width * 0.5)  # 50% of screen width
gameover_height = int(gameover_width * gameover_img.get_height() / gameover_img.get_width())
gameover_img = pygame.transform.scale(gameover_img, (gameover_width, gameover_height))

def background_setting(screen, screen_width, screen_height, scroll_speed=13, night_mode=False):
    """
    Function to handle the background setup.
    
    Args:
        screen: The pygame display surface
        screen_width: Width of the screen
        screen_height: Height of the screen
        scroll_speed: Speed of land scrolling in pixels per frame
        night_mode: Whether to use night theme assets
        
    Returns:
        A tuple containing the background, tap to start, land image surfaces, and scroll speed.
    """
    # Load the background image based on current theme
    background_filename = 'background-night.png' if night_mode else 'dayBackground.png'
    try:
        background_img = pygame.image.load(get_asset_path(background_filename, SPRITE_FOLDER))
    except pygame.error:
        print(f"Error: Could not load {background_filename}")
        pygame.quit()
        sys.exit()

    # Scale the background to fit the screen
    background_img = pygame.transform.scale(background_img, (screen_width, screen_height))
    
    # Load the tap to start image
    try:
        tap_to_start_img = pygame.image.load(get_asset_path('tapToStart.png', SPRITE_FOLDER))
    except pygame.error:
        print("Error: Could not load tapToStart.png")
        pygame.quit()
        sys.exit()
            
    # Scale the tap to start image to be a good size for the screen (half the width)
    tap_width = screen_width // 2
    tap_height = int(tap_width * tap_to_start_img.get_height() / tap_to_start_img.get_width())
    tap_to_start_img = pygame.transform.scale(tap_to_start_img, (tap_width, tap_height))

    # Load the land image
    try:
        land_img = pygame.image.load(get_asset_path('land.png', SPRITE_FOLDER))
    except pygame.error:
        print("Error: Could not load land.png")
        pygame.quit()
        sys.exit()
            
    # Scale the land image to fit the width of the screen and about 10% of the height
    land_height = int(screen_height * 0.17)
    land_img = pygame.transform.scale(land_img, (screen_width, land_height))

    return background_img, tap_to_start_img, land_img, scroll_speed

def bird_mechanics(screen_width, screen_height, night_mode=False):
    """
    Function to handle the bird setup and mechanics.
    
    Args:
        screen_width: Width of the screen
        screen_height: Height of the screen
        night_mode: Whether to use night theme assets
        
    Returns:
        A tuple containing the bird image surfaces, its initial x and y positions, and its size.
    """
    # Choose the bird color based on theme
    bird_prefix = ""
    if night_mode:
        bird_prefix = "redbird-"
    else:
        bird_prefix = "yellowbird-"
    
    # Load the bird images for different states
    try:
        bird_downflap_img = pygame.image.load(get_asset_path(f'{bird_prefix}downflap.png', SPRITE_FOLDER))
        bird_midflap_img = pygame.image.load(get_asset_path(f'{bird_prefix}midflap.png', SPRITE_FOLDER))
        bird_upflap_img = pygame.image.load(get_asset_path(f'{bird_prefix}upflap.png', SPRITE_FOLDER))
    except pygame.error:
        print(f"Error: Could not load {bird_prefix} bird images")
        # Fall back to original bluebird if the colored birds aren't found
        try:
            bird_downflap_img = pygame.image.load(get_asset_path('bluebird-downflap.png', SPRITE_FOLDER))
            bird_midflap_img = pygame.image.load(get_asset_path('bluebird-midflap.png', SPRITE_FOLDER))
            bird_upflap_img = pygame.image.load(get_asset_path('bluebird-upflap.png', SPRITE_FOLDER))
        except pygame.error:
            print("Error: Could not load bluebird images")
            # Fall back to bird.png as last resort
            try:
                bird_downflap_img = pygame.image.load(get_asset_path('bird.png', SPRITE_FOLDER))
                bird_midflap_img = bird_downflap_img
                bird_upflap_img = bird_downflap_img
            except pygame.error:
                print("Error: Could not load any bird images")
                pygame.quit()
                sys.exit()

    # Scale all bird images to quadruple their size
    bird_downflap_img = pygame.transform.scale(bird_downflap_img, 
                                              (bird_downflap_img.get_width() * 4, 
                                               bird_downflap_img.get_height() * 4))
    bird_midflap_img = pygame.transform.scale(bird_midflap_img, 
                                             (bird_midflap_img.get_width() * 4, 
                                              bird_midflap_img.get_height() * 4))
    bird_upflap_img = pygame.transform.scale(bird_upflap_img, 
                                            (bird_upflap_img.get_width() * 4, 
                                             bird_upflap_img.get_height() * 4))

    # Bird position variables - x is centered, y is higher from center
    bird_x = screen_width // 2 - bird_downflap_img.get_width() // 2
    bird_y = (screen_height // 2 - bird_downflap_img.get_height() // 2) - int(screen_height * 0.10)

    return (bird_downflap_img, bird_midflap_img, bird_upflap_img), bird_x, bird_y

def obstacle_generation(screen_width, screen_height, land_height, night_mode=False):
    """
    Function to handle pipe obstacle generation and management.
    
    Args:
        screen_width: Width of the screen
        screen_height: Height of the screen
        land_height: Height of the land element
        night_mode: Whether to use night theme assets
        
    Returns:
        A tuple containing the pipe image surfaces and initial pipe data.
    """
    # Choose pipe image based on theme
    pipe_filename = 'pipe-red.png' if night_mode else 'greenpipe.png'
    
    # Load the pipe image
    try:
        pipe_img = pygame.image.load(get_asset_path(pipe_filename, SPRITE_FOLDER))
    except pygame.error:
        print(f"Error: Could not load {pipe_filename}")
        # Try fallback to green pipe
        try:
            pipe_img = pygame.image.load(get_asset_path('greenpipe.png', SPRITE_FOLDER))
        except pygame.error:
            print("Error: Could not load pipe images")
            pygame.quit()
            sys.exit()
            
    # Scale the pipe image to appropriate size
    pipe_width = int(screen_width * 0.15)  # 15% of screen width
    pipe_height = int(pipe_img.get_height() * (pipe_width / pipe_img.get_width()))
    
    pipe_img = pygame.transform.scale(pipe_img, (pipe_width, pipe_height))
    
    # Create the top pipe by rotating the bottom pipe 180 degrees
    pipe_top_img = pygame.transform.rotate(pipe_img, 180)
    pipe_bottom_img = pipe_img  # Bottom pipe is the original image
    
    # Initialize pipe data (x position, height)
    pipe_gap = int(screen_height * 0.17)  # Reduced gap between pipes
    pipes = []
    
    return pipe_top_img, pipe_bottom_img, pipes, pipe_gap

def generate_pipe(screen_width, screen_height, land_height, pipe_gap):
    """
    Generate a new pipe position where pipes are anchored to ceiling and land
    
    Args:
        screen_width: Width of the screen
        screen_height: Height of the screen
        land_height: Height of the land element
        pipe_gap: Gap between top and bottom pipes
        
    Returns:
        A list containing pipe x position and gap y position
    """
    # Position the pipe beyond the right edge of the screen
    pipe_x = screen_width
    
    # Calculate more strict boundaries for the gap position
    usable_height = screen_height - land_height
    
    # Ensure the gap is never too close to the top or bottom
    # At least 25% from top and 25% from bottom of usable area
    min_gap_y = int(usable_height * 0.25)
    max_gap_y = int(usable_height * 0.75)
    
    # Center of the gap
    gap_y = random.randint(min_gap_y, max_gap_y)
    
    return [pipe_x, gap_y]

def collision_detection(bird_rect, pipes, pipe_top_img, pipe_bottom_img, pipe_gap, passed_pipes):
    """
    Handle collision detection between bird and pipes.
    """
    collision = False
    
    # Create a smaller bird collision rect for more accurate detection
    bird_inset = int(bird_rect.width * 0.1)  # 10% inset
    adjusted_bird_rect = pygame.Rect(
        bird_rect.x + bird_inset,
        bird_rect.y + bird_inset,
        bird_rect.width - (bird_inset * 2),
        bird_rect.height - (bird_inset * 2)
    )
    
    for pipe_index, pipe in enumerate(pipes):
        # Calculate pipe positions
        gap_center_y = pipe[1]
        half_gap = pipe_gap // 2
        
        # Top pipe position
        top_pipe_y = gap_center_y - half_gap - pipe_top_img.get_height()
        
        # Make collision rect better aligned with visual pipe edges
        pipe_width = pipe_top_img.get_width()
        pipe_height = pipe_top_img.get_height()
        
        # Create more precise collision rects for pipes - reduce horizontal inset
        # to make horizontal collision more accurate
        inset_x = int(pipe_width * 0.05)  # Reduced from 10% to 5% for better horizontal collision
        inset_y = 0  # Remove vertical inset completely at the gap edges
        
        # Extend the collision box slightly beyond visual pipes to ensure proper collision
        top_pipe_rect = pygame.Rect(
            pipe[0] + inset_x, 
            top_pipe_y, 
            pipe_width - (inset_x * 2), 
            pipe_height
        )
        
        # Bottom pipe position
        bottom_pipe_y = gap_center_y + half_gap
        bottom_pipe_rect = pygame.Rect(
            pipe[0] + inset_x, 
            bottom_pipe_y, 
            pipe_width - (inset_x * 2), 
            pipe_height
        )
        
        # Check for collision with pipes
        if adjusted_bird_rect.colliderect(top_pipe_rect) or adjusted_bird_rect.colliderect(bottom_pipe_rect):
            collision = True
            
    return collision

def scoring_system(screen_width, screen_height):
    """
    Set up the scoring system with number images.
    
    Args:
        screen_width: Width of the screen
        screen_height: Height of the screen
        
    Returns:
        A dictionary containing number images from 0-9
    """
    # Create a dictionary to store number images
    number_images = {}
    
    # Load all number images (0-9)
    for i in range(10):
        try:
            number_images[i] = pygame.image.load(get_asset_path(f'{i}.png', SPRITE_FOLDER))
        except pygame.error:
            print(f"Warning: Could not load {i}.png")
            # Create a dummy number surface
            font = pygame.font.SysFont(None, 40)
            number_images[i] = font.render(str(i), True, (255, 255, 255))
    
    # Scale all number images to appropriate size (increased from 5% to 8% of screen height)
    digit_height = int(screen_height * 0.08)
    
    for i in range(10):
        original_ratio = number_images[i].get_width() / number_images[i].get_height()
        digit_width = int(digit_height * original_ratio)
        number_images[i] = pygame.transform.scale(number_images[i], (digit_width, digit_height))
    
    return number_images

def draw_score(game_surface, number_images, score, screen_width):
    """
    Draw the current score on the screen using number images.
    
    Args:
        game_surface: The surface to draw on
        number_images: Dictionary of number images
        score: Current score to display
        screen_width: Width of the screen
    """
    # Convert score to string to get individual digits
    score_str = str(score)
    
    # Calculate total width of all digits to center
    total_width = sum(number_images[int(digit)].get_width() for digit in score_str)
    
    # Position the score in the upper part of the screen (3% from top instead of 10%)
    x_pos = (screen_width - total_width) // 2
    y_pos = int(game_area_height * 0.03)
    
    # Draw each digit
    for digit in score_str:
        digit_img = number_images[int(digit)]
        game_surface.blit(digit_img, (x_pos, y_pos))
        x_pos += digit_img.get_width()

# Create a surface for the game area
game_surface = pygame.Surface((screen_width, game_area_height))

# Initialize background and bird mechanics adjusted for game area
background_img, tap_to_start_img, land_img, land_scroll_speed = background_setting(screen, screen_width, game_area_height, night_mode=is_night_theme)
bird_imgs, bird_x_orig, bird_y_orig = bird_mechanics(screen_width, game_area_height, night_mode=is_night_theme)
bird_downflap_img, bird_midflap_img, bird_upflap_img = bird_imgs

# Add collision flash effect surface
flash_surface = pygame.Surface((screen_width, game_area_height), pygame.SRCALPHA)
flash_alpha = 0  # Start with fully transparent
flash_duration = 100  # Flash duration in milliseconds
flash_start_time = 0  # When the flash effect started

# Track the current bird state
current_bird_img = bird_midflap_img
last_bird_action = 0  # 0 = neutral, 1 = jump/touch, -1 = falling

# Add flapping animation variables for start screen
flap_animation_timer = 0
flap_animation_speed = 100  # milliseconds per frame
flap_animation_frames = [bird_downflap_img, bird_midflap_img, bird_upflap_img, bird_midflap_img]  # Animation sequence
current_flap_frame = 0

# Adjust bird position for game area
bird_x = bird_x_orig
bird_y = bird_y_orig 

# Initialize scoring system
number_images = scoring_system(screen_width, game_area_height)

# Initialize obstacle related items
land_height = int(game_area_height * 0.17)
pipe_top_img, pipe_bottom_img, pipes, pipe_gap = obstacle_generation(screen_width, game_area_height, land_height, night_mode=is_night_theme)
pipe_frequency = 3000  # New pipe every 1.5 seconds
last_pipe = pygame.time.get_ticks() - pipe_frequency  # Time since last pipe
pipe_speed = land_scroll_speed  # Same speed as land scrolling

# Bird animation variables
bird_amplitude = 50  # Amplitude of the floating motion
bird_frequency = 2  # Frequency of the floating motion
clock = pygame.time.Clock()

# Land scrolling variables
land_scroll = 0

# Game states
GAME_START = 0
GAME_PLAYING = 1
GAME_OVER = 2
GAME_RESTART = 3  # New state for showing game over message
game_state = GAME_START
gameover_time = 0  # Track when to restart game

# Passed pipes for scoring
passed_pipes = set()
score = 0

# Initialize score tracking time to handle point sound timing
score_time = 0
point_sound_played = False

# Game loop
running = True
start_time = pygame.time.get_ticks()
while running:
    # Get current time for sound timing
    current_time = pygame.time.get_ticks()
    
    # Handle events differently based on game state
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:  # Allow ESC key to exit
                running = False
            elif event.key == pygame.K_SPACE:  # Add spacebar as alternative control
                if game_state == GAME_START:
                    # Change to playing state when spacebar is pressed
                    game_state = GAME_PLAYING
                    bird_velocity = -40  # Initial jump when starting
                    bird_angle = max_upward_angle
                    wing_sound.play()  # Play wing sound on touch
                    current_bird_img = bird_downflap_img  # Show downflap on touch
                    last_bird_action = 1  # Track that we just jumped
                elif game_state == GAME_PLAYING:
                    # Make the bird jump when spacebar is pressed
                    bird_velocity = -40
                    bird_angle = max_upward_angle
                    wing_sound.play()  # Play wing sound on touch
                    current_bird_img = bird_downflap_img  # Show downflap on touch
                    last_bird_action = 1  # Track that we just jumped
        elif event.type == pygame.FINGERDOWN:
            if game_state == GAME_START:
                # Change to playing state when screen is touched
                game_state = GAME_PLAYING
                bird_velocity = -40  # Initial jump when starting
                bird_angle = max_upward_angle
                wing_sound.play()  # Play wing sound on touch
                current_bird_img = bird_downflap_img  # Show downflap on touch
                last_bird_action = 1  # Track that we just jumped
            elif game_state == GAME_PLAYING:
                # Make the bird jump when the screen is touched
                bird_velocity = -40
                bird_angle = max_upward_angle
                wing_sound.play()  # Play wing sound on touch
                current_bird_img = bird_downflap_img  # Show downflap on touch
                last_bird_action = 1  # Track that we just jumped

    # Draw the background
    game_surface.blit(background_img, (0, 0))

    if game_state == GAME_START:
        # Update flapping animation in start screen
        if current_time - flap_animation_timer > flap_animation_speed:
            flap_animation_timer = current_time
            current_flap_frame = (current_flap_frame + 1) % len(flap_animation_frames)
        
        # Draw the bird in the center with the current animation frame
        game_surface.blit(flap_animation_frames[current_flap_frame], (bird_x, bird_y))
        
        # Center the tap to start image on screen
        tap_x = (screen_width - tap_to_start_img.get_width()) // 2
        tap_y = (game_area_height - tap_to_start_img.get_height()) // 2
        game_surface.blit(tap_to_start_img, (tap_x, tap_y))
        
        # Show initial score of 0 on the start screen
        draw_score(game_surface, number_images, 0, screen_width)
        
        # Scroll the land even in start screen
        land_scroll -= land_scroll_speed
        if land_scroll <= -screen_width:
            land_scroll = 0
            
        # Draw two copies of the land for infinite scrolling
        land_y = game_area_height - land_img.get_height()
        game_surface.blit(land_img, (land_scroll, land_y))
        game_surface.blit(land_img, (land_scroll + screen_width, land_y))
    elif game_state == GAME_PLAYING:
        # Apply gravity and update bird position
        prev_y = bird_y  # Remember previous position to determine direction
        
        bird_velocity += gravitational_force
        bird_y += int(bird_velocity)

        # Update bird image based on movement
        if last_bird_action == 1:  # Just jumped
            current_bird_img = bird_downflap_img
            last_bird_action = 0  # Reset after using downflap
        elif bird_y < prev_y:  # Moving upward (y decreasing)
            current_bird_img = bird_midflap_img
        else:  # Falling downward
            current_bird_img = bird_upflap_img

        # Calculate land position for collision detection
        land_y = game_area_height - land_img.get_height()
        
        # Adjust bird angle based on velocity
        if bird_velocity < 0:  # Bird is moving upward
            bird_angle = max_upward_angle
        else:  # Bird is falling
            # Gradually rotate anticlockwise as the bird falls
            bird_angle = max(max_downward_angle, bird_angle - downward_rotation_speed)

        # Rotate the bird image
        rotated_bird = pygame.transform.rotate(current_bird_img, bird_angle)
        
        # Get the rect of the rotated image to ensure the bird stays centered
        rotated_rect = rotated_bird.get_rect(center=(bird_x + bird_midflap_img.get_width()//2, 
                                                    bird_y + bird_midflap_img.get_height()//2))
        
        # Generate pipes
        time_now = pygame.time.get_ticks()
        if time_now - last_pipe > pipe_frequency:
            pipes.append(generate_pipe(screen_width, game_area_height, land_img.get_height(), pipe_gap))
            last_pipe = time_now
        
        # Update pipe positions and handle removal of off-screen pipes
        pipe_removal = []
        for pipe_index, pipe in enumerate(pipes):
            # Move pipe to the left
            pipe[0] -= pipe_speed
            
            # Score when pipe passes the middle of the screen
            pipe_center = pipe[0] + (pipe_top_img.get_width() / 2)
            if pipe_center <= screen_width / 2 and pipe_center > (screen_width / 2) - pipe_speed:
                # Pipe is passing the center of the screen right now
                if game_state == GAME_PLAYING:
                    # Play point sound and increment score
                    point_sound.play()
                    score += 1
            
            # Remove pipes that have moved off the left edge of the screen
            if pipe[0] < -pipe_top_img.get_width():
                pipe_removal.append(pipe_index)
        
        # Remove pipes that are off screen
        for index in sorted(pipe_removal, reverse=True):
            pipes.pop(index)
        
        # Draw pipes
        for pipe in pipes:
            # Calculate gap position
            gap_center_y = pipe[1]
            half_gap = pipe_gap // 2
            
            # Top pipe (upside down) - anchored to the ceiling
            # The bottom of the top pipe should be at gap_center_y - half_gap
            top_pipe_y = gap_center_y - half_gap - pipe_top_img.get_height()
            game_surface.blit(pipe_top_img, (pipe[0], top_pipe_y))
            
            # Bottom pipe - anchored to the ground
            # The top of the bottom pipe should be at gap_center_y + half_gap
            bottom_pipe_y = gap_center_y + half_gap
            game_surface.blit(pipe_bottom_img, (pipe[0], bottom_pipe_y))
        
        # Collision detection for pipes
        bird_rect = rotated_bird.get_rect(topleft=rotated_rect.topleft)
        collision = collision_detection(bird_rect, pipes, pipe_top_img, pipe_bottom_img, pipe_gap, passed_pipes)
        
        # Handle collision with pipes
        if collision and game_state != GAME_OVER:
            hit_sound.play()
            die_sound.play()  # Play die sound once when entering game over state
            game_state = GAME_OVER
            die_sound_played = True  # Mark that we've played the die sound
            
            # Initialize flash effect
            flash_alpha = 180  # Start with high alpha (semi-transparent white)
            flash_start_time = current_time

        # Check for collision with the land
        if bird_y + bird_midflap_img.get_height() > land_y:
            if game_state != GAME_OVER:
                hit_sound.play()
                die_sound.play()  # Play die sound when hitting the ground
                game_state = GAME_OVER
                die_sound_played = True
            bird_y = land_y - bird_midflap_img.get_height()
            bird_velocity = 0  # Stop the bird from falling further

        # Prevent the bird from going off the top of the screen
        if bird_y < 0:
            bird_y = 0
            bird_velocity = 0

        # Scroll the land
        land_scroll -= land_scroll_speed
        if land_scroll <= -screen_width:
            land_scroll = 0
            
        # Draw two copies of the land for infinite scrolling
        land_y = game_area_height - land_img.get_height()
        game_surface.blit(land_img, (land_scroll, land_y))
        game_surface.blit(land_img, (land_scroll + screen_width, land_y))
        
        # Draw the rotated bird
        game_surface.blit(rotated_bird, rotated_rect.topleft)
        
        # Draw the score
        draw_score(game_surface, number_images, score, screen_width)
    elif game_state == GAME_OVER:
        # Apply increased gravity when game over
        bird_velocity += gravitational_force * 1.5
        bird_y += int(bird_velocity)
        
        # Bird always rotates downward in game over state
        bird_angle = max(max_downward_angle, bird_angle - downward_rotation_speed * 2)
        
        # Rotate the bird image (use upflap in game over state as bird is falling)
        rotated_bird = pygame.transform.rotate(bird_upflap_img, bird_angle)
        rotated_rect = rotated_bird.get_rect(center=(bird_x + bird_midflap_img.get_width()//2, 
                                                    bird_y + bird_midflap_img.get_height()//2))
        
        # Check for collision with the land (final resting place)
        land_y = game_area_height - land_img.get_height()
        
        # Fix the bird landing to be exactly on top of the land
        # Check for collision with the land
        if bird_y + bird_midflap_img.get_height() > land_y:
            bird_y = land_y - bird_midflap_img.get_height()
            bird_velocity = 0  # Stop the bird from falling further
        
        # Draw pipes (they stop moving in game over state)
        for pipe in pipes:
            gap_center_y = pipe[1]
            half_gap = pipe_gap // 2
            
            top_pipe_y = gap_center_y - half_gap - pipe_top_img.get_height()
            game_surface.blit(pipe_top_img, (pipe[0], top_pipe_y))
            
            bottom_pipe_y = gap_center_y + half_gap
            game_surface.blit(pipe_bottom_img, (pipe[0], bottom_pipe_y))
        
        # Draw the rotated bird
        game_surface.blit(rotated_bird, rotated_rect.topleft)
        
        # Land no longer scrolls in game over state
        land_y = game_area_height - land_img.get_height()
        game_surface.blit(land_img, (land_scroll, land_y))
        game_surface.blit(land_img, (land_scroll + screen_width, land_y))
        
        # Show game over image
        gameover_x = (screen_width - gameover_img.get_width()) // 2
        gameover_y = (game_area_height - gameover_img.get_height()) // 2
        game_surface.blit(gameover_img, (gameover_x, gameover_y))
        
        # Draw the score (continue to show score in game over state)
        draw_score(game_surface, number_images, score, screen_width)
        
        # Transition to restart state after a delay
        if gameover_time == 0:
            gameover_time = pygame.time.get_ticks()
        elif pygame.time.get_ticks() - gameover_time > 2000:  # 2 seconds delay
            game_state = GAME_RESTART
    elif game_state == GAME_RESTART:
        # Toggle between day and night themes when restarting
        is_night_theme = not is_night_theme
        
        # Reload game assets with new theme
        background_img, tap_to_start_img, land_img, land_scroll_speed = background_setting(
            screen, screen_width, game_area_height, night_mode=is_night_theme)
        bird_imgs, bird_x_orig, bird_y_orig = bird_mechanics(
            screen_width, game_area_height, night_mode=is_night_theme)
        bird_downflap_img, bird_midflap_img, bird_upflap_img = bird_imgs
        pipe_top_img, pipe_bottom_img, pipes, pipe_gap = obstacle_generation(
            screen_width, game_area_height, land_height, night_mode=is_night_theme)
        
        # Update flapping animation frames with new bird images
        flap_animation_frames = [bird_downflap_img, bird_midflap_img, bird_upflap_img, bird_midflap_img]
        
        # Reset game variables for restart
        bird_x = bird_x_orig
        bird_y = bird_y_orig
        bird_velocity = 0
        bird_angle = 0
        pipes = []
        passed_pipes.clear()
        score = 0
        game_state = GAME_START
        gameover_time = 0
        current_bird_img = bird_midflap_img

    # Apply flash effect if active
    if flash_alpha > 0:
        # Calculate how much time has passed since the flash started
        flash_elapsed = current_time - flash_start_time
        
        # Decrease alpha based on elapsed time
        if flash_elapsed < flash_duration:
            # Flash is still active
            flash_surface.fill((255, 255, 255, flash_alpha))
            game_surface.blit(flash_surface, (0, 0))
        else:
            # Flash effect is over
            flash_alpha = 0

    # Fill the screen with black first
    screen.fill((0, 0, 0))
    
    # Draw the game surface onto the main screen at the offset position
    screen.blit(game_surface, (0, game_area_y_offset))

    # Update the display
    pygame.display.flip()

    # Cap the frame rate
    clock.tick(60)

# Quit pygame
pygame.quit()