import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import hashlib
import socket
import threading
from cryptography.fernet import Fernet
import argparse

# Constants
XMAX, YMAX = 1200, 700
SPACESHIP_SPEED = 20
SERVER_PORT = 12345
ENCRYPTION_KEY = Fernet.generate_key()
cipher_suite = Fernet(ENCRYPTION_KEY)

# Initial game state
viewPage = "INTRO"
keyStates = {chr(i): False for i in range(256)}
direction = [False] * 4
laser1Dir, laser2Dir = [False, False], [False, False]
alienLife1, alienLife2 = 100, 100
gameOver = False
xOne, yOne, xTwo, yTwo = 500, 0, 500, 0
laser1, laser2 = False, False
CI = 0
mButtonPressed = False
mouseX, mouseY = 0, 0

# Game assets (simplified for brevity)
LightColor = [(1, 1, 0), (0, 1, 1), (0, 1, 0)]
AlienBody = [(-4, 9), (-6, 0), (0, 0), (0.5, 9), (0.15, 12), (-14, 18), (-19, 10), (-20, 0), (-6, 0)]
AlienCollar = [(-9, 10.5), (-6, 11), (-5, 12), (6, 18), (10, 20), (13, 23), (16, 30), (19, 39), (16, 38),
               (10, 37), (-13, 39), (-18, 41), (-20, 43), (-20.5, 42), (-21, 30), (-19.5, 23), (-19, 20),
               (-14, 16), (-15, 17), (-13, 13), (-9, 10.5)]
AlienFace = [(-6, 11), (-4.5, 18), (0.5, 20), (0, 20.5), (0.1, 19.5), (1.8, 19), (5, 20), (7, 23), (9, 29),
             (6, 29.5), (5, 28), (7, 30), (10, 38), (11, 38), (11, 40), (11.5, 48), (10, 50.5), (8.5, 51), 
             (6, 52), (1, 51), (-3, 50), (-1, 51), (-3, 52), (-5, 52.5), (-6, 52), (-9, 51), (-10.5, 50), 
             (-12, 49), (-12.5, 47), (-12, 43), (-13, 40), (-12, 38.5), (-13.5, 33), (-15, 38), (-14.5, 32), 
             (-14, 28), (-13.5, 33), (-14, 28), (-13.8, 24), (-13, 20), (-11, 19), (-10.5, 12), (-6, 11)]
AlienBeak = [(-6, 21.5), (-6.5, 22), (-9, 21), (-11, 20.5), (-20, 20), (-14, 23), (-9.5, 28), (-7, 27), 
             (-6, 26.5), (-4.5, 23), (-4, 21), (-6, 19.5), (-8.5, 19), (-10, 19.5), (-11, 20.5)]

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
    server_socket.bind(('', SERVER_PORT))
    server_socket.listen(5)
    print("Server started, waiting for connections...")
    while True:
        client_socket, addr = server_socket.accept()
        print(f"Connection from {addr}")
        threading.Thread(target=handle_client, args=(client_socket,)).start()

def handle_client(client_socket):
    while True:
        try:
            data = client_socket.recv(1024)
            if not data:
                break
            decrypted_data = cipher_suite.decrypt(data).decode('utf-8')
            print(f"Received: {decrypted_data}")
        except:
            break
    client_socket.close()

def connect_to_server(server_ip):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((server_ip, SERVER_PORT))
    return client_socket

# Display text on screen
def display_text(x, y, text, size=24, color=(255, 255, 255)):
    font = pygame.font.SysFont("Arial", size)
    surface = font.render(text, True, color)
    screen.blit(surface, (x, y))

# Draw alien
def draw_alien(isPlayer1):
    glColor3f(0, 1, 0) if isPlayer1 else glColor3f(1, 1, 0)
    glBegin(GL_POLYGON)
    for vertex in AlienBody:
        glVertex2fv(vertex)
    glEnd()
    glColor3f(0, 0, 0)
    glBegin(GL_LINE_STRIP)
    for vertex in AlienBody:
        glVertex2fv(vertex)
    glEnd()

def draw_spaceship(x, y, isPlayer1):
    glPushMatrix()
    glTranslatef(x, y, 0)
    draw_alien(isPlayer1)
    glPopMatrix()

def display():
    global alienLife1, alienLife2
    glClear(GL_COLOR_BUFFER_BIT)
    if viewPage == "GAME":
        draw_spaceship(xOne, yOne, True)
        draw_spaceship(xTwo, yTwo, False)
        if laser1:
            log_event("Player 1 fired a laser")
        if laser2:
            log_event("Player 2 fired a laser")
    pygame.display.flip()

def main(args):
    global viewPage, keyStates, mButtonPressed, mouseX, mouseY

    if args.mode == 'server':
        start_server()
    elif args.mode == 'client':
        server_ip = args.ip
        client_socket = connect_to_server(server_ip)
        pygame.init()
        global screen
        screen = pygame.display.set_mode((XMAX, YMAX), DOUBLEBUF | OPENGL)
        pygame.display.set_caption("Galactic Guardians")
        gluOrtho2D(-XMAX//2, XMAX//2, -YMAX//2, YMAX//2)

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    quit()
                elif event.type == pygame.KEYDOWN:
                    keyStates[chr(event.key)] = True
                elif event.type == pygame.KEYUP:
                    keyStates[chr(event.key)] = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mButtonPressed = True
                elif event.type == pygame.MOUSEBUTTONUP:
                    mButtonPressed = False
                elif event.type == pygame.MOUSEMOTION:
                    mouseX, mouseY = event.pos

            display()
            data = f"{xOne},{yOne},{xTwo},{yTwo}"
            encrypted_data = cipher_suite.encrypt(data.encode('utf-8'))
            client_socket.sendall(encrypted_data)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Galactic Guardians Game")
    parser.add_argument('--mode', choices=['server', 'client'], default='server', help="Start as server or client")
    parser.add_argument('--ip', default='127.0.0.1', help="Server IP address (required for client mode)")
    args = parser.parse_args()

    main(args)
