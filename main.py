import pygame
import os
import time
import random
import json
import csv 
import statistics
import matplotlib.pyplot as plt  # For plotting the score graph
pygame.font.init()

WIDTH, HEIGHT = 1000, 1000
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Space Invaders")

# Global score history (stores final scores from each game session)
score_history = []

SCORE_CSV = "score_history.csv"
SCORE_FILE = "score_history.json"

def update_score_graph(new_score):
    """
    Load the existing scores from a CSV file, append the new score,
    compute the mean, median, and mode, then display these statistics in a bar graph.
    """
    # Load existing scores from the CSV file
    scores = []
    try:
        with open(SCORE_CSV, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if row:  # Skip empty rows
                    scores.append(float(row[0]))
    except FileNotFoundError:
        scores = []
    
    # Append the new score
    scores.append(new_score)
    
    # Write the updated scores back to the CSV file
    with open(SCORE_CSV, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        for score in scores:
            writer.writerow([score])
    
    # Compute statistics: mean, median, and mode
    mean_score = statistics.mean(scores)
    median_score = statistics.median(scores)
    try:
        mode_score = statistics.mode(scores)
    except statistics.StatisticsError:
        mode_score = None  # If no unique mode exists

    # Prepare data for the bar graph
    labels = ['Mean', 'Median', 'Mode']
    values = [mean_score, median_score, mode_score if mode_score is not None else 0]
    
    # Create and display the bar graph
    plt.figure()
    plt.bar(labels, values, color=['blue', 'green', 'red'])
    plt.title("Score Statistics")
    plt.ylabel("Score Value")
    plt.ylim(0, max(values) * 1.2 if values and max(values) > 0 else 1)
    plt.show()  # This will display the graph automatically
    plt.close()

# Load images
RED_SPACE_SHIP = pygame.image.load(os.path.join("assets", "pixel_ship_red_small.png"))
GREEN_SPACE_SHIP = pygame.image.load(os.path.join("assets", "pixel_ship_green_small.png"))
BLUE_SPACE_SHIP = pygame.image.load(os.path.join("assets", "pixel_ship_blue_small.png"))
YELLOW_SPACE_SHIP = pygame.image.load(os.path.join("assets", "pixel_ship_yellow.png"))

# Lasers
RED_LASER = pygame.image.load(os.path.join("assets", "pixel_laser_red.png"))
GREEN_LASER = pygame.image.load(os.path.join("assets", "pixel_laser_green.png"))
BLUE_LASER = pygame.image.load(os.path.join("assets", "pixel_laser_blue.png"))
YELLOW_LASER = pygame.image.load(os.path.join("assets", "pixel_laser_yellow.png"))

# Background
BG = pygame.transform.scale(pygame.image.load(os.path.join("assets", "background-black.png")), (WIDTH, HEIGHT))

class Laser:
    def __init__(self, x, y, img):
        self.x = x
        self.y = y
        self.img = img
        self.mask = pygame.mask.from_surface(self.img)

    def draw(self, window):
        window.blit(self.img, (self.x, self.y))

    def move(self, vel):
        self.y += vel

    def off_screen(self, height):
        return not (self.y <= height and self.y >= 0)

    def collision(self, obj):
        return collide(self, obj)

class Ship:
    COOLDOWN = 10

    def __init__(self, x, y, health=100):
        self.x = x
        self.y = y
        self.health = health
        self.ship_img = None
        self.laser_img = None
        self.lasers = []
        self.cool_down_counter = 0

    def draw(self, window):
        window.blit(self.ship_img, (self.x, self.y))
        for laser in self.lasers:
            laser.draw(window)

    def move_lasers(self, vel, obj):
        self.cooldown()
        for laser in self.lasers[:]:
            laser.move(vel)
            if laser.off_screen(HEIGHT):
                self.lasers.remove(laser)
            elif laser.collision(obj):
                obj.health -= 10
                if laser in self.lasers:
                    self.lasers.remove(laser)

    def cooldown(self):
        if self.cool_down_counter >= self.COOLDOWN:
            self.cool_down_counter = 0
        elif self.cool_down_counter > 0:
            self.cool_down_counter += 1

    def shoot(self):
        if self.cool_down_counter == 0:
            laser = Laser(self.x, self.y, self.laser_img)
            self.lasers.append(laser)
            self.cool_down_counter = 1

    def get_width(self):
        return self.ship_img.get_width()

    def get_height(self):
        return self.ship_img.get_height()

class Player(Ship):
    def __init__(self, x, y, health=100):
        super().__init__(x, y, health)
        self.ship_img = YELLOW_SPACE_SHIP
        self.laser_img = YELLOW_LASER
        self.mask = pygame.mask.from_surface(self.ship_img)
        self.max_health = health

    # Modified: now accepts an optional score_container parameter (a list with a single int)
    def move_lasers(self, vel, objs, score_container=None):
        self.cooldown()
        for laser in self.lasers[:]:
            laser.move(vel)
            if laser.off_screen(HEIGHT):
                self.lasers.remove(laser)
            else:
                for obj in objs[:]:
                    if laser.collision(obj):
                        objs.remove(obj)
                        if score_container is not None:
                            score_container[0] += 1  # Increase score by 1 per enemy kill
                        if laser in self.lasers:
                            self.lasers.remove(laser)

    def draw(self, window):
        super().draw(window)
        self.healthbar(window)

    def healthbar(self, window):
        pygame.draw.rect(window, (255,0,0), (self.x, self.y + self.ship_img.get_height() + 10, 
                                               self.ship_img.get_width(), 10))
        pygame.draw.rect(window, (0,255,0), (self.x, self.y + self.ship_img.get_height() + 10, 
                                               self.ship_img.get_width() * (self.health/self.max_health), 10))

class Enemy(Ship):
    COLOR_MAP = {
        "red": (RED_SPACE_SHIP, RED_LASER),
        "green": (GREEN_SPACE_SHIP, GREEN_LASER),
        "blue": (BLUE_SPACE_SHIP, BLUE_LASER)
    }

    def __init__(self, x, y, color, health=100):
        super().__init__(x, y, health)
        self.ship_img, self.laser_img = self.COLOR_MAP[color]
        self.mask = pygame.mask.from_surface(self.ship_img)

    def move(self, vel):
        self.y += vel

    def shoot(self):
        if self.cool_down_counter == 0:
            laser = Laser(self.x-20, self.y, self.laser_img)
            self.lasers.append(laser)
            self.cool_down_counter = 1

def collide(obj1, obj2):
    offset_x = obj2.x - obj1.x
    offset_y = obj2.y - obj1.y
    return obj1.mask.overlap(obj2.mask, (offset_x, offset_y)) is not None

# -----------------------------------------
# Singleplayer Mode (1 Human Player)
# -----------------------------------------
def singleplayer_mode():
    run = True
    FPS = 60
    level = 0
    lives = 5
    score = [0]  # Using a list to allow pass-by-reference updates
    main_font = pygame.font.SysFont("comicsans", 50)
    lost_font = pygame.font.SysFont("comicsans", 60)

    enemies = []
    wave_length = 5
    enemy_vel = 1
    player_vel = 7
    laser_vel = 7

    player = Player(300, 630)
    clock = pygame.time.Clock()

    lost = False
    lost_count = 0

    def redraw_window():
        WIN.blit(BG, (0,0))
        lives_label = main_font.render(f"Lives: {lives}", 1, (255,255,255))
        level_label = main_font.render(f"Level: {level}", 1, (255,255,255))
        score_label = main_font.render(f"Score: {score[0]}", 1, (255,255,255))
        WIN.blit(lives_label, (10, 10))
        WIN.blit(level_label, (WIDTH - level_label.get_width() - 10, 10))
        WIN.blit(score_label, (WIDTH//2 - score_label.get_width()//2, 10))

        for enemy in enemies:
            enemy.draw(WIN)

        player.draw(WIN)

        if lost:
            lost_label = lost_font.render("You Lost!!", 1, (255,255,255))
            WIN.blit(lost_label, (WIDTH/2 - lost_label.get_width()/2, 350))

        pygame.display.update()

    while run:
        clock.tick(FPS)
        redraw_window()

        if lives <= 0 or player.health <= 0:
            lost = True
            lost_count += 1

        if lost:
            if lost_count > FPS * 3:
                run = False
                break
            else:
                continue

        if len(enemies) == 0:
            level += 1
            wave_length += 5
            for i in range(wave_length):
                enemy = Enemy(random.randrange(50, WIDTH-100), random.randrange(-1500, -100),
                              random.choice(["red", "blue", "green"]))
                enemies.append(enemy)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False

        keys = pygame.key.get_pressed()
        if keys[pygame.K_a] and player.x - player_vel > 0:  # left
            player.x -= player_vel
        if keys[pygame.K_d] and player.x + player_vel + player.get_width() < WIDTH:  # right
            player.x += player_vel
        if keys[pygame.K_w] and player.y - player_vel > 0:  # up
            player.y -= player_vel
        if keys[pygame.K_s] and player.y + player_vel + player.get_height() + 15 < HEIGHT:  # down
            player.y += player_vel
        if keys[pygame.K_SPACE]:
            player.shoot()

        for enemy in enemies[:]:
            enemy.move(enemy_vel)
            enemy.move_lasers(laser_vel, player)

            if random.randrange(0, 2*60) == 1:
                enemy.shoot()

            if collide(enemy, player):
                player.health -= 10
                enemies.remove(enemy)
            elif enemy.y + enemy.get_height() > HEIGHT:
                lives -= 1
                enemies.remove(enemy)

        # Update score by passing our score container to move_lasers
        player.move_lasers(-laser_vel, enemies, score_container=score)

    pygame.quit()
    update_score_graph(score[0])

# -----------------------------------------
# Multiplayer Mode (2 Human Players)
# -----------------------------------------
def multiplayer_mode():
    run = True
    FPS = 60
    level = 0
    lives = 5
    score = [0]
    main_font = pygame.font.SysFont("comicsans", 50)
    lost_font = pygame.font.SysFont("comicsans", 60)

    enemies = []
    wave_length = 5
    enemy_vel = 1
    player_vel = 7
    laser_vel = 7

    player1 = Player(150, 630)
    player2 = Player(450, 630)  # Second player uses same ship image

    clock = pygame.time.Clock()

    lost = False
    lost_count = 0

    def redraw_window():
        WIN.blit(BG, (0,0))
        lives_label = main_font.render(f"Lives: {lives}", 1, (255,255,255))
        level_label = main_font.render(f"Level: {level}", 1, (255,255,255))
        score_label = main_font.render(f"Score: {score[0]}", 1, (255,255,255))
        WIN.blit(lives_label, (10, 10))
        WIN.blit(level_label, (WIDTH - level_label.get_width() - 10, 10))
        WIN.blit(score_label, (WIDTH//2 - score_label.get_width()//2, 10))

        for enemy in enemies:
            enemy.draw(WIN)

        player1.draw(WIN)
        player2.draw(WIN)

        if lost:
            lost_label = lost_font.render("You Lost!!", 1, (255,255,255))
            WIN.blit(lost_label, (WIDTH/2 - lost_label.get_width()/2, 350))

        pygame.display.update()

    while run:
        clock.tick(FPS)
        redraw_window()

        if lives <= 0 or player1.health <= 0 or player2.health <= 0:
            lost = True
            lost_count += 1

        if lost:
            if lost_count > FPS * 3:
                run = False
                break
            else:
                continue

        if len(enemies) == 0:
            level += 1
            wave_length += 5
            for i in range(wave_length):
                enemy = Enemy(random.randrange(50, WIDTH-100), random.randrange(-1500, -100),
                              random.choice(["red", "blue", "green"]))
                enemies.append(enemy)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False

        keys = pygame.key.get_pressed()
        # Player 1 controls (WASD and SPACE)
        if keys[pygame.K_a] and player1.x - player_vel > 0:
            player1.x -= player_vel
        if keys[pygame.K_d] and player1.x + player_vel + player1.get_width() < WIDTH:
            player1.x += player_vel
        if keys[pygame.K_w] and player1.y - player_vel > 0:
            player1.y -= player_vel
        if keys[pygame.K_s] and player1.y + player_vel + player1.get_height() + 15 < HEIGHT:
            player1.y += player_vel
        if keys[pygame.K_SPACE]:
            player1.shoot()

        # Player 2 controls (Arrow keys and Right CTRL for shooting)
        if keys[pygame.K_LEFT] and player2.x - player_vel > 0:
            player2.x -= player_vel
        if keys[pygame.K_RIGHT] and player2.x + player_vel + player2.get_width() < WIDTH:
            player2.x += player_vel
        if keys[pygame.K_UP] and player2.y - player_vel > 0:
            player2.y -= player_vel
        if keys[pygame.K_DOWN] and player2.y + player_vel + player2.get_height() + 15 < HEIGHT:
            player2.y += player_vel
        if keys[pygame.K_RCTRL]:
            player2.shoot()

        for enemy in enemies[:]:
            enemy.move(enemy_vel)
            enemy.move_lasers(laser_vel, player1)
            enemy.move_lasers(laser_vel, player2)

            if random.randrange(0, 2*60) == 1:
                enemy.shoot()

            if collide(enemy, player1) or collide(enemy, player2):
                if collide(enemy, player1):
                    player1.health -= 10
                if collide(enemy, player2):
                    player2.health -= 10
                enemies.remove(enemy)
            elif enemy.y + enemy.get_height() > HEIGHT:
                lives -= 1
                enemies.remove(enemy)

        player1.move_lasers(-laser_vel, enemies, score_container=score)
        player2.move_lasers(-laser_vel, enemies, score_container=score)

    pygame.quit()
    update_score_graph(score[0])

# -----------------------------------------
# Simulation Mode (AI-controlled Player) - Simplified AI remains unchanged
# -----------------------------------------
def simulation_mode():
    run = True
    FPS = 60
    level = 0
    lives = 5
    score = [0]
    main_font = pygame.font.SysFont("comicsans", 50)
    lost_font = pygame.font.SysFont("comicsans", 60)

    enemies = []
    wave_length = 5
    enemy_vel = 1.2
    player_vel = 7
    laser_vel = 7

    player = Player(300, 800)
    clock = pygame.time.Clock()

    lost = False
    lost_count = 0

    # AI movement direction: 1 for right, -1 for left
    direction = 1

    def redraw_window():
        WIN.blit(BG, (0,0))
        lives_label = main_font.render(f"Lives: {lives}", 1, (255,255,255))
        level_label = main_font.render(f"Level: {level}", 1, (255,255,255))
        score_label = main_font.render(f"Score: {score[0]}", 1, (255,255,255))
        WIN.blit(lives_label, (10, 10))
        WIN.blit(level_label, (WIDTH - level_label.get_width() - 10, 10))
        WIN.blit(score_label, (WIDTH//2 - score_label.get_width()//2, 10))
        for enemy in enemies:
            enemy.draw(WIN)
        player.draw(WIN)
        if lost:
            lost_label = lost_font.render("You Lost!!", 1, (255,255,255))
            WIN.blit(lost_label, (WIDTH/2 - lost_label.get_width()/2, 350))
        pygame.display.update()

    def ai_control():
        nonlocal direction
        # Simplified AI: move back and forth horizontally
        player.x += player_vel * direction
        if player.x <= 0 or player.x + player.get_width() >= WIDTH:
            direction *= -1
        # Continuously shoot
        player.shoot()

    while run:
        clock.tick(FPS)
        ai_control()
        redraw_window()

        if lives <= 0 or player.health <= 0:
            lost = True
            lost_count += 1

        if lost:
            if lost_count > FPS * 3:
                run = False
                break
            else:
                continue

        if len(enemies) == 0:
            level += 1
            wave_length += 5
            for i in range(wave_length):
                enemy = Enemy(random.randrange(50, WIDTH-100), random.randrange(-1500, -100),
                              random.choice(["red", "blue", "green"]))
                enemies.append(enemy)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False

        for enemy in enemies[:]:
            enemy.move(enemy_vel)
            enemy.move_lasers(laser_vel, player)

            if random.randrange(0, 2*60) == 1:
                enemy.shoot()

            if collide(enemy, player):
                player.health -= 10
                enemies.remove(enemy)
            elif enemy.y + enemy.get_height() > HEIGHT:
                lives -= 1
                enemies.remove(enemy)

        player.move_lasers(-laser_vel, enemies, score_container=score)

    pygame.quit()
    update_score_graph(score[0])

# -----------------------------------------
# Main: Call the appropriate mode based on selection
# -----------------------------------------
def main(mode="singleplayer"):
    if mode == "singleplayer":
        singleplayer_mode()
    elif mode == "multiplayer":
        multiplayer_mode()
    elif mode == "simulation":
        simulation_mode()
    else:
        print("Invalid mode selected.")

# Button class for menu
class Button:
    def __init__(self, x, y, width, height, text):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font_size = int(height * 0.6)  # Adjust font size dynamically
        self.font = pygame.font.SysFont("comicsans", self.font_size)
        self.color = (255, 255, 255)

    def draw(self, window):
        pygame.draw.rect(window, (50, 50, 50), self.rect, border_radius=10)  # Background
        pygame.draw.rect(window, self.color, self.rect, 3, border_radius=10)  # Border

        label = self.font.render(self.text, True, self.color)
        text_x = self.rect.x + (self.rect.width - label.get_width()) // 2
        text_y = self.rect.y + (self.rect.height - label.get_height()) // 2
        window.blit(label, (text_x, text_y))

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

# Main Menu
def main_menu():
    title_font = pygame.font.SysFont("comicsans", 60)  # Bigger title
    button_width, button_height = 250, 70  # Larger buttons
    button_x = (WIDTH - button_width) // 2  # Center buttons horizontally

    buttons = [
        Button(button_x, 300, button_width, button_height, "Singleplayer"),
        Button(button_x, 380, button_width, button_height, "Multiplayer"),
        Button(button_x, 460, button_width, button_height, "Simulation")
    ]

    run = True
    while run:
        WIN.blit(BG, (0, 0))
        title_label = title_font.render("Select Game Mode", True, (255, 255, 255))
        WIN.blit(title_label, (WIDTH // 2 - title_label.get_width() // 2, 200))

        for button in buttons:
            button.draw(WIN)

        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                for button in buttons:
                    if button.is_clicked(event.pos):
                        main(button.text.lower())

    pygame.quit()

main_menu()
