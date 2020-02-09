import asyncio
import json
import keyboard
import websocket
try:
    import thread
except ImportError:
    import _thread as thread
import time
from queue import Queue
import colorama
import os
import random
import sys



serverUrl = "example.com"
serverPort = 1893

if serverUrl == "example.com":
    print("please change Server URL in game.py")
    sys.exit()



colorama.init()


qToServer = Queue(10)
qToClient = Queue(10)
qToScreen = Queue(10)

col = colorama.Fore
colorsAvail = [col.BLUE, col.GREEN, col.YELLOW, col.MAGENTA, col.CYAN, col.BLACK]
shadingsAvail = ["██", "//", "##", "\\\\", "==", "$$", "{}", "++"]


try:
    os.system('cls')
    def clearScreen():
        os.system('cls')
except:
    try:
        os.system('clear')
        def clearScreen():
            os.system('clear')
    except:
        print("Clearing screen not possible...")
        sys.exit()


def diff(first, second):
    second = set(second)
    return [item for item in first if item not in second]


def on_message(ws, message):
    global qToClient
    qToClient.put(message)

def on_error(ws, error):
    print(error)

def on_close(ws):
    print("### closed ###")

def on_open(ws):
    global qToServer
    def run(*args):
        ws.send('{"event": "connect", "name": "KASA"}')
        running = True
        while running:
            if not qToServer.empty():
                cmd = qToServer.get()
                if cmd == "end":
                    running = False
                    break
                #print("sending", cmd)
                ws.send(cmd)
            time.sleep(0.1)
        ws.close()
        print("thread terminating...")
    thread.start_new_thread(run, ())


directionKeys = [["w", "up"], ["a", "left"], ["s", "down"], ["d", "right"]]

class Game:
    def __init__(self):
        print("Starting game")
        self.connected = False
        self.screenBuffer = []
        self.screenBuffer_last = []
        self.direction = ""
        self.screenNeedsRedraw = True
        self.playerId = 0
        self.playerPos = [0,0]
        self.debugMessage = ""
        self.dosRunning = False
        self.playerList = []
        self.playerColors = {}
        self.playerNames = {}
        self.playerScores = {}
        self.screenReady = False
        self.lastScreenPrinted = 0

    def processServerMsg(self):
        global qToClient
        global qToServer
        while not qToClient.empty():
            msg = qToClient.get()
            msg = json.loads(msg)
            #print(msg["event"])
            if msg["event"] == "welcome":
                self.screenBuffer = msg["ownership"]
                self.tailsBuffer = msg["tails"]
                self.playerId = int(msg["player_id"])
                for player in msg["players"]:
                    if int(player["id"]) == self.playerId:
                        self.playerColors[self.playerId] = colorama.Fore.BLUE
                    else:
                        newCol = random.choice(colorsAvail)
                        print(newCol + "added player", player["id"], colorama.Style.RESET_ALL)
                        self.playerColors[int(player["id"])] = newCol
                        colorsAvail.remove(newCol)
                    self.playerNames[int(player["id"])] = player["name"]
                print(self.playerColors)
                self.screenReady = True
            elif msg["event"] == "update":
                currentPlayerList = []
                for player in msg["players"]:
                    currentPlayerList.append(player["id"])
                    pos = player["position"]
                    if int(player["id"]) == self.playerId:
                        self.playerPos = pos
                    if player["id"] != self.screenBuffer[pos[0]][pos[1]]:
                        self.tailsBuffer[pos[0]][pos[1]] = int(player["id"])
                    self.playerNames[int(player["id"])] = player["name"]
                currentPlayerList.sort()
                newPlayers = diff(currentPlayerList, self.playerList)
                droppedPlayers = diff(self.playerList, currentPlayerList)
                self.playerList = currentPlayerList
                #self.debugMessage = "new: " + str(newPlayers) + " drop: " + str(droppedPlayers)

                for player in droppedPlayers:
                    colorsAvail.append(self.playerColors[str(player)])
                for player in newPlayers:
                    newCol = random.choice(colorsAvail)
                    self.playerColors[str(player)] = newCol
                    colorsAvail.remove(newCol)

                newOwnership = msg["new_ownership"]
                #print(newOwnership)
                for owner in newOwnership:
                    #print(owner)
                    for cell in newOwnership[owner]:
                        #print("new cell", cell[0], cell[1], "has val", owner)
                        self.screenBuffer[cell[0]][cell[1]] = int(owner)
                        self.tailsBuffer[cell[0]][cell[1]] = 0


                #self.debugMessage += str(self.playerNames)
                for field in msg["clean_owner"]:
                    self.screenBuffer[field[0]][field[1]] = 0
                for field in msg["clean_tail"]:
                    self.tailsBuffer[field[0]][field[1]] = 0

                self.playerScores = {}
                for line in self.screenBuffer:
                    for player in self.playerList:
                        try:
                            self.playerScores[player] += line.count(player)
                        except:
                            self.playerScores[player] = line.count(player)


            elif msg["event"] == "game over":
                print("Game Over")
                qToServer.put("end")

            elif msg["event"] == "error":
                print("ERROR")
                qToServer.put("end")
                print(msg)





    def renderScreen(self):

        def getPix(x, y , screenBuffer, tailBuffer, prevCol):
            pixVal_screen = int(screenBuffer[x][y])
            pixVal_tail = int(tailBuffer[x][y])
            try:
                if [x, y] == self.playerPos:
                    newCol = colorama.Style.RESET_ALL + colorama.Fore.RED
                elif pixVal_screen == 0 and pixVal_tail == 0:
                    newCol = colorama.Style.RESET_ALL
                elif pixVal_tail != 0:
                    newCol = self.playerColors[pixVal_tail] + colorama.Style.BRIGHT
                elif pixVal_screen != 0 and pixVal_tail == 0:
                    newCol = colorama.Style.RESET_ALL + self.playerColors[pixVal_screen]
                else:
                    newCol = prevCol
            except:
                newCol = colorama.Fore.MAGENTA

            if newCol != prevCol:
                return newCol + "██", newCol
            else:
                return "██", prevCol

        if self.screenReady:
            clearScreen()
            #print("----------------------")
            screenString = colorama.Style.RESET_ALL
            prevCol = ""
            scoreBoard = []
            for key, value in sorted(self.playerScores.items(), key=lambda item: item[1])[::-1]:
                scoreBoard.append([key, value])
            for y in range(len(self.screenBuffer[0])):
                for x in range(len(self.screenBuffer)):
                    #screenString += printPix(pixVal, prevVal)
                    newPix, prevCol = getPix(x, y, self.screenBuffer, self.tailsBuffer, prevCol)
                    screenString += newPix
                if y == 0:
                    screenString += "SCOREBOARD"
                else:
                    try:
                        playerId = scoreBoard[y-1][0]
                        playerScore = scoreBoard[y-1][1]
                        screenString += colorama.Style.RESET_ALL + str(y) + ". "
                        try:
                            screenString += colorama.Style.BRIGHT + self.playerColors[playerId]
                        except:
                            pass
                        screenString += self.playerNames[playerId] + colorama.Style.RESET_ALL + " " +  str(playerScore)
                    except IndexError:
                        pass
                screenString += ("\n")
            #self.debugMessage += str(self.playerColors)
            screenString += self.debugMessage
            #screenString += str(scoreBoard)

            print(screenString)
            self.debugMessage = ""
            frameTime = time.time() - self.lastScreenPrinted
            #print(1/frameTime)
            self.lastScreenPrinted = time.time()
            #print("----------------------")
            #print(len(self.screenBuffer), len(self.screenBuffer[0]))
        #cellCount = 0
        #for line in self.screenBuffer:
        #    cellCount += line.count(self.playerId)
        #print("cellCount:", cellCount, "of", self.playerId)

    def getUserIn(self):
        global qToServer
        if keyboard.is_pressed("esc"):
            qToServer.put("end")
        newDirection = ""
        for key in directionKeys:
            if keyboard.is_pressed(key[0]):
                newDirection = key[1]
        if newDirection == "":
            newDirection = self.direction
        if newDirection != self.direction:
            self.direction = newDirection
            dirEvent = '{"event": "go_direction", "direction": "' + self.direction + '"}'
            qToServer.put(dirEvent)
            #print("going in direction", self.direction)

    def run(self):
        self.processServerMsg()
        self.renderScreen()
        self.getUserIn()
        #time.sleep(0.1)

    def gameLoop(self):
        while True:
            self.run()


def getUserIn(game):
    global qToServer
    while True:
        if keyboard.is_pressed("esc"):
            qToServer.put("end")
            break
        newDirection = ""
        for key in directionKeys:
            if keyboard.is_pressed(key[0]):
                newDirection = key[1]
        if newDirection == "":
            newDirection = game.direction
        if newDirection != game.direction:
            game.direction = newDirection
            dirEvent = '{"event": "go_direction", "direction": "' + game.direction + '"}'
            qToServer.put(dirEvent)
            #print("going in direction", game.direction)
        if keyboard.is_pressed("g") and not self.dosRunning:
            self.debugMessage = "starting DOS"
            self.dosRunning = True
            thread.start_new_thread(performDOS, (self))
        if keyboard.is_pressed("h"):
            self.debugMessage = "stopping DOS"
            self.dosRunning = False

def performDOS(game):
    global qToServer
    while game.dosRunning:
        qToServer.put("Hallo Server!")
        time.sleep(0.1)
    game.debugMessage = "DOS stopped, thread terminated"

game = Game()

#thread.start_new_thread(getUserIn, (game,))
thread.start_new_thread(game.gameLoop, ())


serverString = "ws://" + serverUrl + ":" + str(serverPort)


#websocket.enableTrace(True)
ws = websocket.WebSocketApp(serverString,
                          on_message = on_message,
                          on_error = on_error,
                          on_close = on_close)
ws.on_open = on_open
ws.run_forever()
