import socket
import threading
import queue
import json
import datetime
import os
import shared
import ipaddress
from cryptography.hazmat.primitives.asymmetric import rsa, dh, padding
from cryptography.hazmat.primitives import serialization, hashes
import struct
from pathlib import Path
import mimetypes
import time
from tkinter import DoubleVar
import shared
from better_profanity import profanity

# CONNECTION FUNCTIONS

amServer = None
running = False

hostListenIp = None
hostConnectIp = None
port = None
server = None
serverConnection = None
serverAdress = None
messageClient = None
waitingForRequest = False
nextId = 0
partnerIP = None
localIP = None
username = None
excpectingChunk = False
sendQueue = queue.Queue()
logQueue = queue.Queue()
incomingFileTransfers = []
profanity.load_censor_words()
            
def findLanIp():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            lanIpv4 = s.getsockname()[0]
        return lanIpv4
    except socket.error:
        return None

def isIpReal(ip):
    try:
        return ipaddress.IPv4Address(ip).is_private
    except ipaddress.AddressValueError:
        return False

def isProfane(text):
    return profanity.contains_profanity(text)

def getUserName():
    if os.path.isfile(shared.findAbsPath("prefs.txt")):
        with open(shared.findAbsPath("prefs.txt"), "r") as f:
            try:
                text = f.read()
                if json.loads(text)["username"] != None:
                    return json.loads(text)["username"]
            except:
                pass
    return None

def setUserName(username: str):
    with open(shared.findAbsPath("prefs.txt"), "w") as f:
        newDict = {
            "username": username
        }
        f.write(json.dumps(newDict))

def chatThreadLogger():
    global logQueue, amServer
    startupTime = datetime.datetime.now().strftime("%H-%M-%S_%d.%m.%Y")
    logFilePathIteration = 0
    while os.path.isfile(shared.findAbsPath("chats", f"{startupTime}_{logFilePathIteration}.txt")):
        logFilePathIteration += 1
    with open(shared.findAbsPath("chats", f"{startupTime}_{logFilePathIteration}.txt"), "a") as f:
        while True:
            while not logQueue.empty():
                item = logQueue.get()    
                f.write(item + "\n")
            f.flush()
            time.sleep(0.1)
    
def launchServerThreadGUI():
    global port, hostListenIp, server, serverConnection, serverAdress, amServer, partnerIP, localIP, running
    if port != None:
        return
    hostListenIp = "0.0.0.0"
    port = 5000
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((hostListenIp, port))
    server.listen()
    try:
        serverConnection, serverAdress = server.accept()
    except OSError:
        return
    running = True
    partnerIP = serverAdress[0]
    serverConnection.settimeout(1)
    server.settimeout(1)
    localIP = findLanIp()
    shared.guiQueue.put(["networkStatus", f"Connected to {partnerIP} as server!", True])
    shared.guiQueue.put(["readyConn", True])
    threading.Thread(target=receivingThreadGUI, daemon=True).start()
    threading.Thread(target=sendingThreadGUI, daemon=True).start()
    threading.Thread(target=chatThreadLogger, daemon=True).start()
    amServer = True

def closeServerLaunchGUI():
    global server
    if server != None:
        server.close()

def launchClientThreadGUI(ipv4):
    global hostConnectIp, port, messageClient, amServer, partnerIP, localIP, running
    hostConnectIp = ipv4
    port = 5000
    messageClient = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    messageClient.settimeout(2.0)
    try:
        messageClient.connect((hostConnectIp, 5000))
    except OSError:
        return
    except TimeoutError:
        shared.guiQueue.put("connectAbort", f"Could not find server at {ipv4}. Check for spelling errors, and that both you and the server are on the same network.")
        return
    messageClient.settimeout(None)
    running = True
    partnerIP = ipv4
    localIP = findLanIp()
    shared.guiQueue.put(["networkStatus", f"Connected to {partnerIP} as client!", True])
    shared.guiQueue.put(["readyConn", True])
    threading.Thread(target=receivingThreadGUI, daemon=True).start()
    threading.Thread(target=sendingThreadGUI, daemon=True).start()
    threading.Thread(target=chatThreadLogger, daemon=True).start()
    amServer = False

def closeClientLaunchGUI():
    global messageClient
    if messageClient != None:
        messageClient.close()

def closeConnectionGUI():
    global amServer, hostConnectIp, hostListenIp, port, server, serverConnection, serverAdress, messageClient, running, sendQueue
    if amServer != None:
        if amServer == True:
            try:
                server.shutdown(socket.SHUT_RDWR)
            except:
                pass
            try:
                serverConnection.shutdown(socket.SHUT_RDWR)
            except:
                pass
            server.close()
            serverConnection.close()
        elif amServer == False:
            try:
                messageClient.shutdown(socket.SHUT_RDWR)
            except:
                pass
            messageClient.close()
        amServer = None
        hostConnectIp = None
        hostListenIp = None
        port = None
        server = None
        serverConnection = None
        serverAdress = None
        messageClient = None
        running = False
        sendQueue = queue.Queue()
        shared.guiQueue.put(["readyConn", False])
        shared.guiQueue.put(["networkStatus", "", False])
    else:
        shared.guiQueue.put(["readyConn", False])
        shared.guiQueue.put(["networkStatus", "", False])

def scanDecodedDataGUI(dict):
    global nextId, excpectingChunk
    if dict["communication"] == True:
        nextId += 1
    if dict["type"] == "msg":
        logQueue.put(json.dumps(dict))
        print(dict["username"])
        shared.guiQueue.put(["msg", dict["content"], dict["sender"], dict["username"] if dict["username"] != None else dict["sender"]])
    elif dict["type"] == "transferRequest":
        shared.guiQueue.put(["transRequest", False, dict, None])
        shared.guiQueue.put(["sysMsg", f"{dict["sender"]} has requested to send the file <{dict["name"]}> of type {dict["mime"]} to {dict["recipient"]} (YOU)"])
    elif dict["type"] == "transferReject":
        shared.guiQueue.put(["transReject", dict["idToRemove"]])
        shared.guiQueue.put(["sysMsg", f"{dict["sender"]} has rejected {dict["sender"]}'s (YOU) request to send file <{dict["fileName"]}>"])
        print("Reject received")
    elif dict["type"] == "fileChunk":
        excpectingChunk = [dict["chunkLen"], dict["targetTransId"]]
        shared.guiQueue.put(["statUpdate", dict["targetTransId"], dict["eta"], dict["speed"], dict["percent"]])
        return True
    elif dict["type"] == "fileAccept":
        shared.guiQueue.put(["activateTransfer", dict["targetTransId"], DoubleVar(), "0 Seconds", "0 KB/S"])
        shared.guiQueue.put(["sysMsg", f"{dict["sender"]} (YOU) has accepted a file transfer from {dict["recipient"]}"])
        incomingFileTransfers.append([dict["saveLocation"], dict["targetTransId"], os.path.join(os.path.dirname(dict["saveLocation"]), f"{dict["targetTransId"]}.downloading")])
    elif dict["type"] == "fileDone":
        shared.guiQueue.put(["fileDone", dict["targetTransId"]])
        itemToRemove = None
        for item in incomingFileTransfers:
            if item[1] == dict["targetTransId"]:
                itemToRemove = item
        if itemToRemove == None:
            return
        os.replace(itemToRemove[2], itemToRemove[0])
        incomingFileTransfers.remove(itemToRemove)
    elif dict["type"] == "transferCancel":
        shared.guiQueue.put(["transCancel", dict["idToRemove"]])
    return False

def receivingThreadGUI():
    global amServer, messageClient, serverConnection, nextId, running, excpectingChunk
    while running:
        try:
            if amServer == True:
                lengthData = b""
                while len(lengthData) < 4:
                    chunk = serverConnection.recv(4 - len(lengthData))
                    if not chunk:
                        closeConnectionGUI()
                        return
                    lengthData += chunk
                lengthData = struct.unpack("!I", lengthData)[0]
                msg = b""
                while len(msg) < lengthData:
                    chunk = serverConnection.recv(lengthData - len(msg))
                    if not chunk:
                        closeConnectionGUI()
                        return
                    msg += chunk
                decodedData = json.loads(msg.decode())
                expect = scanDecodedDataGUI(decodedData)
                if expect:
                    chunk = b""
                    if amServer:
                        while len(chunk) < excpectingChunk[0]:
                            chunkPart = serverConnection.recv(excpectingChunk[0] - len(chunk))
                            if not chunkPart:
                                closeConnectionGUI()
                                return
                            chunk += chunkPart
                    else:
                        while len(chunk) < excpectingChunk[0]:
                            chunkPart = serverConnection.recv(excpectingChunk[0] - len(chunk))
                            if not chunkPart:
                                closeConnectionGUI()
                                return
                            chunk += chunkPart
                    correctTransfer = None
                    for transfer in incomingFileTransfers:
                        if transfer[1] == excpectingChunk[1]:
                            correctTransfer = transfer
                            break
                    if correctTransfer == None:
                        continue
                    with open(correctTransfer[2], "ab") as f:
                        f.write(chunk)
                    
                    excpectingChunk = False
            elif amServer == False:
                lengthData = b""
                while len(lengthData) < 4:
                    chunk = messageClient.recv(4 - len(lengthData))
                    if not chunk:
                        closeConnectionGUI()
                        return
                    lengthData += chunk
                lengthData = struct.unpack("!I", lengthData)[0]
                msg = b""
                while len(msg) < lengthData:
                    chunk = messageClient.recv(lengthData - len(msg))
                    if not chunk:
                        closeConnectionGUI()
                        return
                    msg += chunk
                decodedData = json.loads(msg.decode())
                expect = scanDecodedDataGUI(decodedData)
                if expect:
                    chunk = b""
                    if amServer:
                        while len(chunk) < excpectingChunk[0]:
                            chunkPart = serverConnection.recv(excpectingChunk[0] - len(chunk))
                            if not chunkPart:
                                closeConnectionGUI()
                                return
                            chunk += chunkPart
                    else:
                        while len(chunk) < excpectingChunk[0]:
                            chunkPart = messageClient.recv(excpectingChunk[0] - len(chunk))
                            if not chunkPart:
                                closeConnectionGUI()
                                return
                            chunk += chunkPart
                    correctTransfer = None
                    for transfer in incomingFileTransfers:
                        if transfer[1] == excpectingChunk[1]:
                            correctTransfer = transfer
                            break
                    if correctTransfer == None:
                        continue
                    with open(correctTransfer[2], "ab") as f:
                        f.write(chunk)
                    
                    excpectingChunk = False


        except TimeoutError:
            continue
        except Exception as e:
            if amServer == True:
                # print("Start server exception: " + str(e) + " End server exception")
                continue
            elif amServer == False:
                # print("Start client exception: " + str(e) + " End client exception")
                continue
            if amServer != None:
                closeConnectionGUI()
            break

def writeIdentityKeysGUI():
    os.makedirs(shared.findAbsPath("KEYS"), exist_ok=True)
    if os.path.exists(shared.findAbsPath("KEYS", "serverPrivate.pem")) and os.path.exists(shared.findAbsPath("KEYS", "serverPublic.pem")):
        return
    privateIdentityKey = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with open(shared.findAbsPath("KEYS", "serverPrivate.pem"), "wb") as private:
        private.write(privateIdentityKey.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.PKCS8, encryption_algorithm=serialization.NoEncryption()))
    with open(shared.findAbsPath("KEYS", "serverPublic.pem"), "wb") as public:
        public.write(privateIdentityKey.public_key().public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo))

def sendMsgGUI(msg):
    global amServer, messageClient, serverConnection, serverAdress, nextId, sendQueue
    if msg.strip() != "":
        try:
            if amServer == None:
                return
            else:
                messageDictionary = {
                    "type": "msg",
                    "content": profanity.censor(msg),
                    "timestamp": datetime.datetime.now().strftime("Sent at %H:%M:%S on %d/%m/%Y"),
                    "timezone": datetime.datetime.now().astimezone().tzname(),
                    "sender": findLanIp(),
                    "recipient": partnerIP,
                    "communicationID": nextId,
                    "communication": True,
                    "id": nextId,
                    "username": getUserName()
                }
                logQueue.put(json.dumps(messageDictionary))
                nextId += 1
                shared.guiQueue.put(["msg", messageDictionary["content"], "YOU", messageDictionary["username"] if messageDictionary["username"] != None else "YOU"])
                sendQueue.put([messageDictionary])
        except:
            closeConnectionGUI()

def sendFileRequestGUI(path):
    global amServer, messageClient, serverConnection, serverAdress, nextId, sendQueue
    pathLibPath = Path(path)
    mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
    requestDictionary = {
        "type": "transferRequest",
        "timestamp": datetime.now().strftime("Sent at %H:%M:%S on %d/%m/%Y"),
        "timezone": datetime.now().astimezone().tzname(),
        "sender": findLanIp(),
        "recipient": partnerIP,
        "fileSize": os.path.getsize(path),
        "name": pathLibPath.name,
        "extension": pathLibPath.suffix,
        "mime": mime,
        "path": path,
        "communication": True,
        "id": nextId
    }
    nextId += 1
    shared.guiQueue.put(["transRequest", True, requestDictionary, DoubleVar(), "0 Seconds", "0 KB/S"])
    shared.guiQueue.put(["sysMsg", f"{requestDictionary["sender"]} (YOU) has requested to send the file <{requestDictionary["name"]}> of type {requestDictionary["mime"]} to {requestDictionary["recipient"]}"])
    sendQueue.put([requestDictionary])

def sendRejectionFileGUI(id, name):
    global amServer, messageClient, serverConnection, nextId, sendQueue
    rejectDictionary = {
        "type": "transferReject",
        "timestamp": datetime.now().strftime("Sent at %H:%M:%S on %d/%m/%Y"),
        "timezone": datetime.now().astimezone().tzname(),
        "sender": findLanIp(),
        "recipient": partnerIP,
        "communication": True,
        "id": nextId,
        "idToRemove": id,
        "fileName": name
    }
    nextId += 1
    shared.guiQueue.put(["sysMsg", f"{rejectDictionary["sender"]} (YOU) has rejected {rejectDictionary["sender"]}'s request to send file <{rejectDictionary["fileName"]}>"])
    sendQueue.put([rejectDictionary])

def sendCloseFileGUI(id):
    global sendQueue, nextId
    cancelDictionary = {
        "type": "transferCancel",
        "timestamp": datetime.now().strftime("Sent at %H:%M:%S on %d/%m/%Y"),
        "timezone": datetime.now().astimezone().tzname(),
        "sender": findLanIp(),
        "recipient": partnerIP,
        "communication": True,
        "id": nextId,
        "idToRemove": id
    }
    nextId += 1
    sendQueue.put([cancelDictionary])

def sendFileThreadGUI(size, path, id):
    global running
    sent = 0
    startTime = time.time()
    with open(path, "rb") as f:
        while running:
            chunk = f.read(64 * 1024)
            if not chunk:
                break
            sent += len(chunk)
            timeElapsed = time.time() - startTime
            speed = sent / timeElapsed if timeElapsed > 0 else 0
            eta = (size - sent) / speed if speed > 0 else 0
            chunkDict = {
                "type": "fileChunk",
                "timestamp": datetime.now().strftime("Sent at %H:%M:%S on %d/%m/%Y"),
                "timezone": datetime.now().astimezone().tzname(),
                "sender": findLanIp(),
                "recipient": partnerIP,
                "communication": False,
                "targetTransId": id,
                "chunkLen": len(chunk),
                "percent": sent / size * 100,
                "time": timeElapsed,
                "speed": speed,
                "eta": eta
            }
            sendQueue.put([chunkDict, chunk])
            shared.guiQueue.put(["statUpdate", chunkDict["targetTransId"], chunkDict["eta"], chunkDict["speed"], chunkDict["percent"]])
    doneDict = {
        "type": "fileDone",
        "timestamp": datetime.now().strftime("Sent at %H:%M:%S on %d/%m/%Y"),
        "timezone": datetime.now().astimezone().tzname(),
        "sender": findLanIp(),
        "recipient": partnerIP,
        "communication": False,
        "targetTransId": id
    }
    sendQueue.put([doneDict])

def sendFileAccept(id, name, saveLocation, size, path):
    global nextId, sendQueue
    acceptDict = {
        "type": "fileAccept",
        "timestamp": datetime.now().strftime("Sent at %H:%M:%S on %d/%m/%Y"),
        "timezone": datetime.now().astimezone().tzname(),
        "sender": findLanIp(),
        "recipient": partnerIP,
        "communication": True,
        "targetTransId": id,
        "id": nextId,
        "saveLocation": saveLocation,
        "fileSize": size
    }
    nextId += 1
    shared.guiQueue.put(["sysMsg", f"{acceptDict["sender"]} (YOU) has accepted a file transfer from {acceptDict["recipient"]}"])
    sendQueue.put([acceptDict]) 

def sendingThreadGUI():
    global running, amServer, serverConnection, messageClient, sendQueue
    while running:
        while not sendQueue.empty():
            dictArray = sendQueue.get()
            # print(dictArray[0]["type"])
            comType = dictArray[0]["type"]
            if comType in ("msg", "transferReject", "transferRequest", "transferCancel", "fileAccept", "fileDone"):
                try:
                    jsonData = json.dumps(dictArray[0]).encode()
                    lengthStruct = struct.pack("!I", len(jsonData))
                    dataToSend = lengthStruct + jsonData
                    if amServer:
                        serverConnection.sendall(dataToSend)
                    else:
                        messageClient.sendall(dataToSend)
                except:
                    continue
            elif comType == "fileChunk":
                try:
                    jsonDataChunk = json.dumps(dictArray[0]).encode()
                    lengthStructChunk = struct.pack("!I", len(jsonDataChunk))
                    dataToSendChunk = lengthStructChunk + jsonDataChunk
                    if amServer:
                        serverConnection.sendall(dataToSendChunk)
                        serverConnection.sendall(dictArray[1])
                    else:
                        messageClient.sendall(dataToSendChunk)
                        messageClient.sendall(dictArray[1])
                except:
                    continue