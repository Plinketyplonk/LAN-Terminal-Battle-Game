from random import randint

import pickle

import os, sys

def resource_path(relative_path): # stolen from my coursework project, because apparently the config file doesnt exist, still doesnt exist after using this lol (ITS RIGHT THERE, ig its just a college issue)
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)



class weapon():
    def __init__(self, dmg, splash_dmg, name):
        self.name = name
        
        self.dmg = dmg
        self.splash_dmg = splash_dmg

    def use(self, target_team, target):
        target_team[target].damage(self.dmg)

        for i in range(len(target_team)):
            target_team[i].damage(self.splash_dmg)



class person():
    def __init__(self, kind):
        self.alive = True
        self.kind = kind
        
        if self.kind == "light":
            self.max_hp = 12
            self.evade = 0.5
            self.aresnal = [weapon(6, 0, "sword")]

        elif self.kind == "heavy":
            self.max_hp = 20
            self.evade = 0.1
            self.aresnal = [weapon(5, 2, "maul")]

        elif self.kind == "glass cannon":
            self.max_hp = 5
            self.evade = 0.3
            self.aresnal = [weapon(8, 1, "cannon")]

        else:
            print(f"INVALID PERSON CREATED : {kind}\nDefaulted to light")
            self.kind = "light"
            self.max_hp = 12
            self.evade = 0.5
            self.aresnal = [weapon(6, 0, "sword")]
            
        self.hp = self.max_hp

    def damage(self, dmg_points):
        if self.evade < randint(0,10)/10: # if not dodged
            self.hp -= dmg_points

            if self.hp <= 0:
                self.hp = 0
                self.alive = False

    def attack(self, chosen_wep, target_team, target):
        self.aresnal[chosen_wep].use(target_team, target)



def display():
    print(f"\n\n          TURN {turn}\n")
    
    print("ENEMY TEAM")
    j = 0
    for i in enemy_team:
        print(f"{j} {i.kind} : HP = [{i.hp}/{i.max_hp}]")
        j+=1

    print("\n\n\nPLAYER TEAM")
    j = 0
    for i in player_team:
        print(f"{j} {i.kind} : HP = [{i.hp}/{i.max_hp}]")
        j+=1


def select_unit(team):
    selected = -1
    
    while selected == -1:
        flag = False
        try:
            temp_selc = int(input("Unit (type their ID): "))
        except:
            print("Try typing a number...")
            flag = True
        if not flag:
            if temp_selc < 0 or temp_selc > len(team) -1:
                print("Number out of range, try again.")
            elif not team[temp_selc].alive:
                print("Unit dead, try again.")
            else:
                selected = temp_selc
            
    print(f"Selected unit: {selected} {team[selected].kind}")
    return selected


def select_move():
    print("\nChoose a unit to use")
    unit_id = select_unit(player_team)

    print("Choose a weapon:")
    options = []
    for i in player_team[unit_id].aresnal:
        print(f" - {i.name}")
        options.append(i.name)

    chosen_wep = "none"
    while chosen_wep == "none":
        temp_cho = input("Weapon: ")
        try:
            temp_cho = int(temp_cho)

            if temp_cho > -1 and temp_cho < len(options):
                chosen_wep = temp_cho
        except:
            temp_cho = temp_cho.lower()
            
            for i in range(len(options)):
                if temp_cho == options[i]:
                    chosen_wep = i

    print("\nChoose a unit to target")
    target_id = select_unit(enemy_team)

    player_team[unit_id].attack(chosen_wep, enemy_team, target_id)

    data_to_send = pickle.dumps((f"Enemy used {unit_id}'s {player_team[unit_id].aresnal[chosen_wep].name}.", enemy_team))

    return data_to_send



# global variables, im sorry greg

def create_team(teams, i):
    unit_names = teams[i].split(",")
    this_team = []
    for name in unit_names:
        this_team.append(person(name))
    return this_team

try:
    with open(resource_path("config.csv"), "rt") as f:
        teams = f.read()
        teams = teams.splitlines()
        player_team = create_team(teams, 0)
        enemy_team = create_team(teams, 1)
except: # if loading the config doesnt work, just use the default
    player_team = [person("light"), person("heavy"), person("glass cannon")]
    enemy_team = [person("light"), person("heavy"), person("glass cannon")]

turn = 0

playing = True

def player_live():
    global playing, enemy_team
    one_alive = False
    for i in player_team:
        if i.alive:
            one_alive = True

    if not one_alive:
        playing = False
        print("\n\n       YOU LOSE!      ")
        data_to_send = pickle.dumps(("\n\nYOU WON!", enemy_team))
    else:
        data_to_send = "nvm"
    return data_to_send



# ------------------------ NETWORK CODE (and turns lol) ---------------------------

import socket


def host():
    global turn, player_team, enemy_team, playing
    HOST = "0.0.0.0"  # Standard loopback interface address (localhost) --- ngl i copied this part from stackoverflow, i have little idea what this comment is really about
    PORT = 65432  # Port to listen on (non-privileged ports are > 1023)
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        conn, addr = s.accept()
        with conn:
            print(f"Connected by {addr}")
            data = pickle.dumps((player_team, enemy_team)) # send the other player the config you have for teams
            conn.sendall(data)
            
            while playing:
                turn += 1
                display() # shows units and stats
                print("\n\nYOUR TURN")
                data = player_live()
                if playing:
                    data = select_move()
                conn.sendall(data) # send other player the resulting data from your turn
                print("\n\nTHEIR TURN")
                data = conn.recv(1024) # recieve
                message, player_team = pickle.loads(data)
                print(message)
                if message == "\n\nYOU WON!":
                    playing = False
                    break


def client(HOST : str, PORT : int):
    global turn, player_team, enemy_team, playing

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))

        data = s.recv(1024) # recieve
        enemy_team, player_team = pickle.loads(data)
        display() # shows units and stats
        while playing:
                print("\n\nTHEIR TURN")
                data = s.recv(1024) # recieve
                message, player_team = pickle.loads(data)
                print(message)
                if message == "\n\nYOU WON!":
                    playing = False
                    break
                print("\n\nYOUR TURN")
                turn += 1
                display() # shows units and stats
                data = player_live()
                if playing:
                    data = select_move()
                s.sendall(data) # send other player the resulting data from your turn


if input("Enter '#' to host: ") == "#":
    print("You are hosting.")
    hostname = socket.gethostname()
    IP = socket.gethostbyname(hostname)
    print(f"Your host name is {hostname} and your IP is {IP} with port 65432")
    host()
else:
    print("You are a client.")
    ip = input("Host IP: ")
    port = int(input("Host Port: "))
    client(ip, port)

input("\nProgram Finished")

