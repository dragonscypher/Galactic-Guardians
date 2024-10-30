import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import hashlib
import socket
import threading
from cryptography.fernet import Fernet
import argparse
import time
import random

# Constants
XMAX, YMAX = 1200, 700
SPACESHIP_SPEED = 5
LASER_SPEED = 10
ALIEN_SPEED = 2
SERVER_PORT = 12345
ENCRYPTION_KEY = Fernet.generate_key()
cipher_suite = Fernet(ENCRYPTION_KEY)

# Initial game state
viewPage = "START"
xOne, yOne = -400, -300
xTwo, yTwo = 400, -300
lasers = []
alien_positions = []
alien_spawn_timer = 0
alien_spawn_interval = 2000  # in milliseconds
key_states = {K_w: False, K_s: False, K_a: False, K_d: False, K_UP: False, K_DOWN: False, K_LEFT: False, K_RIGHT: False}
scores = {"Player 1": 0, "Player 2": 0}
game_over = False

# Blockchain Implementation
class Block:
    def __init__(self, index, data, previous_hash):
        self.index = index
        self.timestamp = pygame.time.get_ticks()
        self.data = data
        self.previous_hash = previous_hash
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        sha = hashlib.sha256()
        sha.update((str(self.index) + str(self.timestamp) + str(self.data) + str(self.previous_hash)).encode('utf-8'))
        return sha.hexdigest()

class Blockchain:
    def __init__(self):
        self.chain = [self.create_genesis_block()]

    def create_genesis_block(self):
        return Block(0, "Genesis Block", "0")

    def get_latest_block(self):
        return self.chain[-1]

    def add_block(self, new_block):
        new_block.previous_hash = self.get_latest_block().hash
        new_block.hash = new_block.calculate_hash()
        self.chain.append(new_block)

# Initialize blockchain
game_chain = Blockchain()

def log_event(event_data):
    new_block = Block(len(game_chain.chain), event_data, game_chain.get_latest_block().hash)
    game_chain.add_block(new_block)

# Network Communication
def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('', SERVER_PORT))
    server_socket.listen(5)
    print("Server started, waiting for connections...")
    server_socket.settimeout(10)
    try:
        client_socket, addr = server_socket.accept()
        client_socket.settimeout(60)
        print(f"Connection from {addr}")
        threading.Thread(target=handle_client, args=(client_socket,)).start()
    except socket.timeout:
        print("No client connected within 10 seconds, starting game in single-player mode.")
        game_loop(None)

def handle_client(client_socket):
    while True:
        try:
            data = client_socket.recv(1024)
            if not data:
                break
            decrypted_data = cipher_suite.decrypt(data).decode('utf-8')
            print(f"Received: {decrypted_data}")
        except socket.timeout:
            print("Connection timed out. Closing client socket.")
            break
        except Exception as e:
            print(f"Error: {e}")
            break
    client_socket.close()

def connect_to_server(server_ip):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    client_socket.settimeout(60)
    try:
        client_socket.connect((server_ip, SERVER_PORT))
    except socket.error as e:
        print(f"Could not connect to server: {e}")
        return None
    return client_socket

# Pygame and OpenGL Setup
def setup_pygame():
    pygame.init()
    screen = pygame.display.set_mode((XMAX, YMAX), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Galactic Guardians")
    glClearColor(0.0, 0.0, 0.0, 1.0)  # Set background color to black
    gluOrtho2D(-XMAX // 2, XMAX // 2, -YMAX // 2, YMAX // 2)
    return screen

# Draw Stars Background
def draw_stars():
    glPointSize(2)
    glBegin(GL_POINTS)
    glColor3f(1, 1, 1)
    for _ in range(100):
        glVertex2f(random.randint(-XMAX // 2, XMAX // 2), random.randint(-YMAX // 2, YMAX // 2))
    glEnd()

# Draw Spaceship
def draw_spaceship(x, y, isPlayer1):
    glPushMatrix()
    glTranslatef(x, y, 0)
    if isPlayer1:
        glColor3f(0, 1, 0)  # Green for Player 1
    else:
        glColor3f(1, 1, 0)  # Yellow for Player 2

    # Draw body of the spaceship
    glBegin(GL_TRIANGLES)
    glVertex2f(0, 30)  # Top point of the triangle
    glVertex2f(-20, -20)  # Bottom left point of the triangle
    glVertex2f(20, -20)  # Bottom right point of the triangle
    glEnd()

    # Draw wings
    glBegin(GL_QUADS)
    glVertex2f(-25, -10)
    glVertex2f(-15, -10)
    glVertex2f(-15, -30)
    glVertex2f(-25, -30)

    glVertex2f(15, -10)
    glVertex2f(25, -10)
    glVertex2f(25, -30)
    glVertex2f(15, -30)
    glEnd()

    # Draw cockpit
    glColor3f(0.5, 0.5, 0.5)
    glBegin(GL_QUADS)
    glVertex2f(-5, 0)
    glVertex2f(5, 0)
    glVertex2f(5, -10)
    glVertex2f(-5, -10)
    glEnd()

    glPopMatrix()

# Draw Laser
def draw_lasers():
    global lasers
    glColor3f(1, 0, 0)
    glBegin(GL_LINES)
    for laser in lasers:
        x, y = laser
        glVertex2f(x, y)
        glVertex2f(x, y + 20)
    glEnd()

# Draw Aliens
def draw_aliens():
    global alien_positions
    glColor3f(1, 0, 1)  # Magenta for aliens
    for alien in alien_positions:
        x, y = alien
        glPushMatrix()
        glTranslatef(x, y, 0)
        glBegin(GL_TRIANGLES)
        glVertex2f(0, 20)
        glVertex2f(-15, -15)
        glVertex2f(15, -15)
        glEnd()
        glPopMatrix()

# Draw Score
def draw_score():
    pygame.font.init()
    font = pygame.font.SysFont('Arial', 20)
    score_text = f"Player 1: {scores['Player 1']}  Player 2: {scores['Player 2']}"
    text_surface = font.render(score_text, True, (255, 255, 255))
    text_data = pygame.image.tostring(text_surface, "RGBA", True)
    glWindowPos2d(-XMAX // 2 + 10, YMAX // 2 - 30)
    glDrawPixels(text_surface.get_width(), text_surface.get_height(), GL_RGBA, GL_UNSIGNED_BYTE, text_data)

# Draw Start Page
def draw_start_page():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    pygame.font.init()
    font = pygame.font.SysFont('Arial', 50)
    text_surface = font.render("Press ENTER to Start", True, (255, 255, 255))
    text_data = pygame.image.tostring(text_surface, "RGBA", True)
    glWindowPos2d(-text_surface.get_width() // 2, 0)
    glDrawPixels(text_surface.get_width(), text_surface.get_height(), GL_RGBA, GL_UNSIGNED_BYTE, text_data)
    pygame.display.flip()

# Draw Game Over Page
def draw_game_over_page():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    pygame.font.init()
    font = pygame.font.SysFont('Arial', 50)
    text_surface = font.render(f"Game Over! Player 1: {scores['Player 1']}  Player 2: {scores['Player 2']}  Press R to Restart", True, (255, 0, 0))
    text_data = pygame.image.tostring(text_surface, "RGBA", True)
    glWindowPos2d(XMAX // 2 - text_surface.get_width() // 2, YMAX // 2 - text_surface.get_height() // 2)
    glDrawPixels(text_surface.get_width(), text_surface.get_height(), GL_RGBA, GL_UNSIGNED_BYTE, text_data)
    pygame.display.flip()

# Display Function
def display(screen):
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    if viewPage == "START":
        draw_start_page()
    elif viewPage == "GAME":
        draw_stars()
        draw_spaceship(xOne, yOne, True)
        draw_spaceship(xTwo, yTwo, False)
        draw_lasers()
        draw_aliens()
        draw_score()
    elif viewPage == "GAME_OVER":
        draw_game_over_page()
    pygame.display.flip()

# Main Game Loop
def game_loop(client_socket):
    global xOne, yOne, xTwo, yTwo, lasers, alien_positions, alien_spawn_timer, key_states, scores, viewPage, game_over
    screen = setup_pygame()
    clock = pygame.time.Clock()

    while True:
        current_time = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            elif event.type == pygame.KEYDOWN:
                if viewPage == "START" and event.key == pygame.K_RETURN:
                    viewPage = "GAME"
                    viewPage = "GAME"
                elif viewPage == "GAME_OVER" and event.key == pygame.K_r:
                    # Reset game state
                    xOne, yOne = -400, -300
                    xTwo, yTwo = 400, -300
                    lasers = []
                    alien_positions = []
                    scores = {"Player 1": 0, "Player 2": 0}
                    game_over = False
                    viewPage = "START"
                    # Reset game state
                    xOne, yOne = -400, -300
                    xTwo, yTwo = 400, -300
                    lasers = []
                    alien_positions = []
                    scores = {"Player 1": 0, "Player 2": 0}
                    game_over = False
                    viewPage = "START"
                if event.key in key_states:
                    key_states[event.key] = True
                if event.key == pygame.K_SPACE and viewPage == "GAME":
                    lasers.append((xOne, yOne + 30))  # Fire laser from Player 1
                    log_event("Player 1 fired a laser")
            elif event.type == pygame.KEYUP:
                if event.key in key_states:
                    key_states[event.key] = False

        if viewPage == "GAME" and not game_over:
            # Update player positions based on key states
            if key_states[K_w]:
                yOne += SPACESHIP_SPEED
            if key_states[K_s]:
                yOne -= SPACESHIP_SPEED
            if key_states[K_a]:
                xOne -= SPACESHIP_SPEED
            if key_states[K_d]:
                xOne += SPACESHIP_SPEED

            # Computer player 2 logic if no client connected
            if client_socket is None:
                # Computer Player 2: Rule-based decision making
                if abs(yTwo - yOne) > 5:
                    if yTwo < yOne:
                        yTwo += SPACESHIP_SPEED // 2
                    elif yTwo > yOne:
                        yTwo -= SPACESHIP_SPEED // 2
                if abs(xTwo - xOne) > 5:
                    if xTwo < xOne:
                        xTwo += SPACESHIP_SPEED // 2
                    elif xTwo > xOne:
                        xTwo -= SPACESHIP_SPEED // 2

                # Dodge incoming lasers
                for laser in lasers:
                    laser_x, laser_y = laser
                    if abs(laser_x - xTwo) < 30 and laser_y < yTwo:
                        if random.choice([True, False]):
                            xTwo += SPACESHIP_SPEED // 2
                        else:
                            xTwo -= SPACESHIP_SPEED // 2

                # Fire laser at random intervals
                if random.random() < 0.02:
                    lasers.append((xTwo, yTwo + 30))  # Fire laser from Player 2
                    log_event("Player 2 fired a laser")  # Fire laser from Player 2
                    scores["Player 2"] += 1
                    log_event("Player 2 fired a laser")

            # Update laser positions and check for collisions with aliens
            updated_lasers = []
            for laser in lasers:
                x, y = laser
                y += LASER_SPEED
                if y < YMAX // 2:
                    updated_lasers.append((x, y))
                    # Check for collision with aliens
                    for alien in alien_positions:
                        alien_x, alien_y = alien
                        if alien_x - 15 < x < alien_x + 15 and alien_y - 15 < y < alien_y + 15:
                            alien_positions.remove(alien)
                            if x == xOne:
                                scores["Player 1"] += 10
                                log_event("Alien destroyed by Player 1")
                            else:
                                scores["Player 2"] += 10
                                log_event("Alien destroyed by Player 2")
            lasers = updated_lasers

            # Spawn aliens periodically
            if current_time - alien_spawn_timer > alien_spawn_interval:
                alien_positions.append((random.randint(-XMAX // 2, XMAX // 2), YMAX // 2))
                alien_spawn_timer = current_time

            # Move aliens
            alien_positions = [(x, y - ALIEN_SPEED) for (x, y) in alien_positions if y > -YMAX // 2]

            # Check for collisions between aliens and player
            for alien in alien_positions:
                alien_x, alien_y = alien
                if alien_x - 20 < xOne < alien_x + 20 and alien_y - 20 < yOne < alien_y + 20:
                    viewPage = "GAME_OVER"
                    log_event("Player 1 hit by alien. Game Over.")
                    game_over = True

            # Send player position to server if client_socket is available
            if client_socket:
                try:
                    data = f"{xOne},{yOne},{xTwo},{yTwo}"
                    encrypted_data = cipher_suite.encrypt(data.encode('utf-8'))
                    client_socket.sendall(encrypted_data)
                except (ConnectionAbortedError, ConnectionResetError, socket.timeout) as e:
                    print(f"Connection error: {e}. Closing client socket.")
                    client_socket.close()
                    client_socket = None

        # Update display
        display(screen)
        clock.tick(60)

# Main Function
def main(args):
    global viewPage
    if args.mode == 'server':
        start_server()
    elif args.mode == 'client':
        server_ip = args.ip
        client_socket = connect_to_server(server_ip)
        game_loop(client_socket)
    else:
        viewPage = "START"
        game_loop(None)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Galactic Guardians Game")
    parser.add_argument('--mode', choices=['server', 'client'], default='server', help="Start as server or client")
    parser.add_argument('--ip', default='127.0.0.1', help="Server IP address (required for client mode)")
    args = parser.parse_args()

    main(args)
