if __name__ == "__main__":
    print("Do not close this window!")

import tkinter
from tkinter import ttk, filedialog, font
import engine
import shared
import threading
import os
import shutil
import atexit
from functools import partial

# Declare variables
window = None
notebook = None
testTab = None
chatTab = None
connectTab = None
peerTab = None
accountTab = None
contactsTab = None
fileTab = None
connectWidgets = {}
chatWidgets = {}
testWidgets = {}
peerWidgets = {}
accountWidgets = {}
contactsWidgets = {}
fileWidgets = {}
fileItems = []

def setup():
    global window, notebook, testTab, connectTab, chatTab, sendIcon, peerTab, accountTab, contactsTab, fileTab
    # Declare window
    window = tkinter.Tk()
    window.title("LanCom")
    window.columnconfigure(0, weight=1)
    window.columnconfigure(1, weight=1)
    window.geometry("400x200")
    window.minsize(200, 100)

    # Declare notebook
    notebook = ttk.Notebook(window)
    notebook.pack(fill="both", expand=True)

    # Declare tabs
    testTab = tkinter.Frame(notebook)
    testTab.columnconfigure(0, weight=1)
    testTab.columnconfigure(1, weight=1)
    # notebook.add(testTab, text="Test")
    chatTab = tkinter.Frame(notebook)
    chatTab.columnconfigure(0, weight=1)
    chatTab.columnconfigure(1, weight=0)
    chatTab.rowconfigure(0, weight=1)  
    notebook.add(chatTab, text="Chat", state="disabled")
    fileTab = tkinter.Frame(notebook)
    fileTab.columnconfigure(0, weight=1)
    fileTab.columnconfigure(1, weight=1)
    fileTab.columnconfigure(2, weight=1)
    notebook.add(fileTab, text="File", state="disabled")
    connectTab = tkinter.Frame(notebook)
    connectTab.columnconfigure(0, weight=1)
    connectTab.columnconfigure(1, weight=1)
    notebook.add(connectTab, text="Connect")
    peerTab = tkinter.Frame(notebook)
    notebook.add(peerTab, text="Peer", state="disabled")
    accountTab = tkinter.Frame(notebook)
    accountTab.columnconfigure(0, weight=1)
    accountTab.columnconfigure(1, weight=1)
    notebook.add(accountTab, text="Account")
    contactsTab = tkinter.Frame(notebook)
    contactsTab.columnconfigure(0, weight=1)
    contactsTab.columnconfigure(1, weight=1)
    notebook.add(contactsTab, text="Contacts")

    # Font
    defaultFont = font.nametofont("TkDefaultFont")
    defaultFont.configure(family="Arial", size=8)

def refreshTabs():
    global chatWidgets, fileWidgets, connectWidgets, accountWidgets, contactsWidgets
    clearTab(chatWidgets, fileWidgets, connectWidgets, accountWidgets, contactsWidgets)
    constructChatTab()

def readQueue():
    global connectWidgets, chatWidgets, fileItems, fileWidgets
    while not shared.guiQueue.empty():
        command = shared.guiQueue.get()
        if command[0] == "printRequest":
            print(command[1])
        elif command[0] == "networkStatus":
            if command[2] == None:
                connectWidgets[(0 ,0)].config(text=command[1])
            elif command[2] == True:
                clearTab(connectWidgets)
                statusUpdate = tkinter.Label(connectTab, text=command[1], anchor="center")
                statusUpdate.grid(row=0, column=0, columnspan=2)
                connectWidgets[(0, 0)] = statusUpdate
                closeBtn = tkinter.Button(connectTab, text="Close Connection", anchor="center", command=engine.closeConnectionGUI)
                closeBtn.grid(row=1, column=0, columnspan=2)
                connectWidgets[(1, 0)] = closeBtn
            elif command[2] == False:
                clearTab(connectWidgets)
                constructSettingsTab()
        elif command[0] == "readyConn":
            if command[1] == True:
                notebook.tab(chatTab, state="normal")
                notebook.tab(peerTab, state="normal")
                notebook.tab(fileTab, state="normal")
            else:
                notebook.tab(chatTab, state="disabled")
                notebook.tab(peerTab, state="disabled")
                notebook.tab(fileTab, state="disabled")
        elif command[0] == "msg":
            atBottom = chatWidgets[(0, 1)].yview()[1] == 1.0
            chatWidgets[(0, 1)].config(state="normal")
            if command[2] == "YOU":
                tag = "green"
            else:
                tag="blue"
            chatWidgets[(0, 1)].insert("end", f"{command[3]}: {command[1]}\n", tag)
            chatWidgets[(0, 1)].config(state="disabled")
            if atBottom:
                chatWidgets[(0, 1)].yview_moveto(1.0)
        elif command[0] == "transRequest":
            fileItems.append([command[1], command[2]])
            clearTab(fileWidgets)
            constructFileTab()
        elif command[0] == "transReject":
            for item in fileItems:
                if item[1]["id"] == command[1]:
                    item[1]["type"] = "rejFile"
            clearTab(fileWidgets)
            constructFileTab()
        elif command[0] == "sysMsg":
            atBottom = chatWidgets[(0, 1)].yview()[1] == 1.0
            chatWidgets[(0, 1)].config(state="normal")
            chatWidgets[(0, 1)].insert("end", f"SYS: {command[1]}\n", "red")
            chatWidgets[(0, 1)].config(state="disabled")
            if atBottom:
                chatWidgets[(0, 1)].yview_moveto(1.0)
        elif command[0] == "activateTransfer":
            activateFileItem(command[1])
        elif command[0] == "transCancel":
            for item in fileItems:
                if item[1]["id"] == command[1]:
                    item[1]["type"] = "cancelFile"
            clearTab(fileWidgets)
            constructFileTab()
        elif command[0] == "statUpdate":
            neededItem = None
            for i, item in enumerate(fileItems):
                if item[1]["id"] == command[1]:
                    neededItem = item
                    fileItems[i][1]["eta"] = command[2]
                    fileItems[i][1]["speed"] = command[3]
                    fileItems[i][1]["percent"] = command[4]
            if neededItem == None:
                continue
            baseRow = fileItems.index(neededItem) * 3 + 1
            fileWidgets[(baseRow, 1)].config(text=command[2])
            fileWidgets[(baseRow, 2)].config(text=command[3])
            fileWidgets[(baseRow+1, 0)].config()
        elif command[0] == "connectAbort":
            clearTab(connectWidgets)
            constructSettingsTab(command[1])
    window.after(100, readQueue)

def clearTab(*widgets):
    for a in widgets:
        for w in a.values():
            if w is not None:
                w.destroy()
        w.clear()

def askForFile(title, *types):
    returnV = None
    path = filedialog.askopenfilename(title=title, filetypes=[*types])
    if path:
        returnV = path
    return returnV

def removeFileItem(id):
    global fileItems
    for item in fileItems:
        if item[1]["id"] == id:
            fileItems.remove(item)

def activateFileItem(id):
    global fileItems
    for i, item in enumerate(fileItems):
        if item[1]["id"] == id:
            fileItems[i][1]["type"] = "activeTransfer"
            fileItems[i][1]["percent"] = None
            fileItems[i][1]["speed"] = None
            fileItems[i][1]["eta"] = None
    clearTab(fileWidgets)
    constructFileTab()

def getPathById(id):
    global fileItems
    for item in fileItems:
        if item[1]["id"] == id:
            return item[1]["path"]

def findHumanDataSize(bytes: int):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if bytes < 1024:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024

# TEST TAB
def onBtnClickTest():
    if testWidgets[(1, 0)].get().strip() == "":
        testWidgets[(1, 1)].config(text="No text found!")
    else:
        testWidgets[(1, 1)].config(text=testWidgets[(1, 0)].get())
    testWidgets[(1, 0)].delete(0, tkinter.END)

def printAThing():
    if testWidgets[(1, 0)].get().strip() == "":
        testWidgets[(1, 1)].config(text="No text found!")
    else:
        engine.printAThing(testWidgets[(1, 0)].get())
    testWidgets[(1, 0)].delete(0, tkinter.END)

def constructTestTab():
    # Construct test tab
    greeting = tkinter.Label(testTab, text="Say something! ➤", font=("Arial", 8), anchor="center")
    greeting.grid(row=0, column=0, columnspan=2)
    testWidgets[(0, 0)] = greeting

    entry = tkinter.Entry(testTab, font=("Arial", 12))
    entry.grid(row=1, column=0, padx=10)
    testWidgets[(1, 0)] = entry

    usertext = tkinter.Label(testTab, text="No text entered...", font=("Arial", 8))
    usertext.grid(row=1, column=1, padx=10)
    testWidgets[(1, 1)] = usertext

    button = tkinter.Button(testTab, text="Gimme ur text", command=onBtnClickTest, font=("Arial", 8))
    button.grid(row=2, column=0, columnspan=2, padx=10, sticky="ew")
    testWidgets[(2, 0)] = button

    otherBoi = tkinter.Button(testTab, text="Print a thing", command=printAThing, font=("Arial", 8))
    otherBoi.grid(row=3, column=0, columnspan=2)
    testWidgets[(3, 0)] = otherBoi

# SETTINGS TAB
def cancelLaunchServer():
    global connectWidgets
    engine.closeServerLaunchGUI()
    clearTab(connectWidgets)
    constructSettingsTab()

def launchServerClick():
    global connectWidgets
    connectWidgets[(1, 0)].destroy()
    connectWidgets[(1, 1)].destroy()
    cancelBtn = tkinter.Button(connectTab, text="Cancel", font=("Arial", 8), anchor="center", command=cancelLaunchServer)
    cancelBtn.grid(row=1, column=0)
    connectWidgets[(1, 0)] = cancelBtn
    progress = tkinter.Label(connectTab, text="Preparing...", font=("Arial", 8), anchor="center")
    progress.grid(row=1, column=1)
    connectWidgets[(1, 1)] = progress
    try:
        connectWidgets[(1, 1)].config(text=engine.findLanIp())
    except:
        connectWidgets[(1, 1)].config(text="Error ocurred!")
        return
    connectWidgets[(0, 0)].config(text="Waiting for client...")
    threading.Thread(target=engine.launchServerThreadGUI, daemon=True).start()

def cancelWaitForLaunchClient():
    global connectWidgets
    clearTab(connectWidgets)
    constructSettingsTab()

def launchClientCancel():
    engine.closeClientLaunchGUI()
    clearTab(connectWidgets)
    constructSettingsTab()

def launchClientClick():
    global connectWidgets
    ip = connectWidgets[(1, 0)].get().strip()
    connectWidgets[(1, 0)].delete(0, tkinter.END)
    if ip == "":
        if (3, 0) in connectWidgets:
            connectWidgets[(3, 0)].destroy()
        errorMsg = tkinter.Label(connectTab, text="No IP detected in text box!", font=("Arial", 8), anchor="center", fg="red")
        errorMsg.grid(row=3, column=0, columnspan=2, sticky="ew")
        connectWidgets[(3, 0)] = errorMsg
        return
    elif engine.isIpReal(ip) == False:
        if (3, 0) in connectWidgets:
            connectWidgets[(3, 0)].destroy()
        errorMsg = tkinter.Label(connectTab, text="Specified IP not formatted correctly, or invalid!", font=("Arial", 8), anchor="center", fg="red")
        errorMsg.grid(row=3, column=0, columnspan=2, sticky="ew")
        connectWidgets[(3, 0)] = errorMsg
        return
    clearTab(connectWidgets)
    connectingIP = tkinter.Label(connectTab, text=ip, font=("Arial", 8), anchor="center")
    connectingIP.grid(row=1, column=0, sticky="ew")
    connectWidgets[(1, 0)] = connectingIP
    cancelBtn = tkinter.Button(connectTab, text="Cancel", font=("Arial", 8), anchor="center", command=launchClientCancel)
    cancelBtn.grid(row=1, column=1)
    connectWidgets[(1, 1)] = cancelBtn
    status = tkinter.Label(connectTab, text="Waiting for server...", font=("Arial", 8), anchor="center")
    status.grid(row=0, column=0, columnspan=2, sticky="ew")
    connectWidgets[(0 ,0)] = status
    threading.Thread(target=engine.launchClientThreadGUI, args=(ip,), daemon=True).start()

def launchClientLaunchClick():
    global connectWidgets
    connectWidgets[(1, 0)].destroy()
    connectWidgets[(1, 1)].destroy()
    cancelBtn = tkinter.Button(connectTab, text="Cancel", font=("Arial", 8), anchor="center", command=cancelWaitForLaunchClient)
    cancelBtn.grid(row=2, column=0, columnspan=2)
    connectWidgets[(2, 0)] = cancelBtn
    launchBtn = tkinter.Button(connectTab, text="Launch", font=("Arial", 8), anchor="center", command=launchClientClick)
    launchBtn.grid(row=1, column=1)
    connectWidgets[(1, 1)] = launchBtn
    inputIp = tkinter.Entry(connectTab, font=("Arial", 8))
    inputIp.grid(row=1, column=0)
    inputIp.bind("<Return>", lambda event: launchClientClick())
    connectWidgets[(1, 0)] = inputIp

def constructSettingsTab(error = None):
    # Construct settings tab
    global connectWidgets
    networkStatus = tkinter.Label(connectTab, text="Status: No Connection", font=("Arial", 8), anchor="center")
    networkStatus.grid(row=0, column=0, columnspan=2, sticky="ew")
    connectWidgets[(0, 0)] = networkStatus
    launchServer = tkinter.Button(connectTab, text="Launch Server", font=("Arial", 8), anchor="center", command=launchServerClick)
    launchServer.grid(row=1, column=0)
    connectWidgets[(1, 0)] = launchServer
    launchClient = tkinter.Button(connectTab, text="Launch Client", font=("Arial", 8), anchor="center", command=launchClientLaunchClick)
    launchClient.grid(row=1, column=1)
    connectWidgets[(1, 1)] = launchClient
    if error != None:
        errorMsg = tkinter.Label(connectTab, text=error, font=("Arial", 8), anchor="center")
        errorMsg.grid(row=2, column=0, columnspan=2, sticky="ew")
        connectWidgets[(2, 0)] = errorMsg

# Chat tab functions
def sendAMsg():
    msgText = chatWidgets[(1, 0)].get()
    chatWidgets[(1, 0)].delete(0, tkinter.END)
    threading.Thread(target=engine.sendMsgGUI, args=(msgText,), daemon=True).start()

def constructChatTab():
    # Construct chat tab
    global chatWidgets
    chatFrame = ttk.Frame(chatTab)
    chatFrame.grid(row=0, column=0, sticky="nsew", columnspan=2)
    chatFrame.rowconfigure(0, weight=1)
    chatFrame.columnconfigure(0, weight=1)
    chatWidgets[(0, 0)] = chatFrame
    convoBox = tkinter.Text(chatFrame, state="disabled", wrap="word")
    convoBox.grid(row=0, column=0, sticky="nsew")
    convoBox.tag_config("green", foreground="green")
    convoBox.tag_config("blue", foreground="blue")
    convoBox.tag_config("red", foreground="red")
    chatWidgets[(0, 1)] = convoBox
    scrollBar = tkinter.Scrollbar(chatFrame, command=convoBox.yview)
    scrollBar.grid(row=0, column=1, sticky="ns")
    convoBox.config(yscrollcommand=scrollBar.set)
    chatBox = tkinter.Entry(chatTab, font=("Arial", 8))
    chatBox.grid(row=1, column=0, sticky="ew")
    chatBox.bind("<Return>", lambda event: sendAMsg())
    chatWidgets[(1, 0)] = chatBox
    sendButton = tkinter.Button(chatTab, text="➤", anchor="center", command=sendAMsg)
    sendButton.grid(row=1, column=1)
    chatWidgets[(1, 1)] = sendButton

# Account tab functions
def tryChangeUsername():
    global accountWidgets, update
    newName = accountWidgets[(1, 0)].get().strip()
    update = True
    accountWidgets[(1, 0)].delete(0, tkinter.END)
    try:
        accountWidgets[(2, 0)].destroy()
        accountWidgets[(2, 0)] = None
    except:
        pass
    notificationText = f"Username successfuly updated to <{newName}>"
    if engine.isProfane(newName):
        update = False
        notificationText = "Please retype your username without profanity. Such behaviour is not acceptable on this platform. Nothing was changed."
    if newName == "":
        update = False
        notificationText = "No new username detected. Nothing was changes."
    print(update)
    print(newName)
    if update:
        engine.setUserName(username=newName)
    notification = tkinter.Label(accountTab, text=notificationText)
    notification.grid(row=2, column=0, sticky="ew", columnspan=2)
    accountWidgets[(2, 0)] = notification

def constructAccountTab():
    global accountWidgets
    userName = engine.getUserName()
    statusLabel = tkinter.Label(accountTab, text="You have not yet made an account! This means that all people who message you will not know who you are and only see your IP, and that some features may not be availlable for you. Register by entering your new name below:" if (not os.path.isfile(shared.findAbsPath("prefs.txt"))) or (userName == None) else f"You are currently registered! Use the menu below to change or view your username. Your username is: {userName if userName != None else "Username not found!"}")
    statusLabel.grid(row=0, column=0, sticky="ew", columnspan=2)
    accountWidgets[(0, 0)] = statusLabel
    newName = tkinter.Entry(accountTab)
    newName.grid(row=1, column=0)
    accountWidgets[(1, 0)] = newName
    confirm = tkinter.Button(accountTab, text="Confirm New Username", command=tryChangeUsername)
    confirm.grid(row=1, column=1)
    accountWidgets[(1, 1)] = confirm

# Contact tab function
def savePublicKey():
    # window.withdraw()
    try:
        fileSrc = shared.findAbsPath("KEYS", "serverPublic.pem")
        extension = os.path.splitext(fileSrc)[1]
        if os.path.exists(fileSrc):
            destination = filedialog.asksaveasfilename(title="Save public encryption key...", defaultextension=".pem", filetypes=[("PEM files", "*.pem")], initialfile="serverPublic.pem")
            if destination:
                base, ext = os.path.splitext(destination)
                if ext == "":
                    destination = base + extension
                shutil.copy2(fileSrc, destination)
    finally:
        # window.deiconify()
        print("")

def resetContactsTab():
    global contactsWidgets
    clearTab(contactsWidgets)
    constructContactsTab()

def addContact():
    if contactsWidgets[(1, 1)].get() == "":
        contactsWidgets[(1, 0)].config(fg="red")

def createContactLaunchMenu():
    global contactsWidgets
    clearTab(contactsWidgets)
    instructions = tkinter.Label(contactsTab, text="Create new contact:", anchor="center")
    instructions.grid(row=0, column=0, columnspan=2)
    chatWidgets[(0, 0)] = instructions
    nameLabel = tkinter.Label(contactsTab, text="Name:", anchor="center")
    nameLabel.grid(row=1, column=0)
    contactsWidgets[(1, 0)] = nameLabel
    name = tkinter.Entry(contactsTab)
    name.grid(row=1, column=1)
    contactsWidgets[(1, 1)] = name
    cancel = tkinter.Button(contactsTab, text="Cancel", anchor="center", command=resetContactsTab)
    cancel.grid(row=2, column=0)
    contactsWidgets[(2, 0)] = cancel
    nextBtn = tkinter.Button(contactsTab, text="Next", anchor="center", command=addContact)
    nextBtn.grid(row=2, column=1)
    contactsWidgets[(2, 1)] = nextBtn

def constructContactsTab():
    global contactsWidgets
    getPublicKey = tkinter.Button(contactsTab, text="Download Public Key", anchor="center", command=savePublicKey)
    getPublicKey.grid(row=0, column=0, columnspan=2)
    contactsWidgets[(0, 0)] = getPublicKey
    createContact = tkinter.Button(contactsTab, text="Create Contact", anchor="center", command=createContactLaunchMenu)
    createContact.grid(row=1, column=0, columnspan=2)
    contactsWidgets[(1, 0)] = createContact

# File tab
def startTransfer():
    global fileWidgets
    path = askForFile("What file do you wish to transfer?", ("All files", "*.*"))
    if path == None or False:
        return
    else:
        engine.sendFileRequestGUI(path)

def rejectTransfer(id, name):
    for item in fileItems:
        if item[1]["id"] == id:
            item[1]["type"] = "rejFile"
    clearTab(fileWidgets)
    constructFileTab()
    engine.sendRejectionFileGUI(id, name)

def acceptTransfer(id, name, ext, mime, size, path):
    saveAsDestination = filedialog.asksaveasfilename(title=f"Where do you want <{name}> to go?", defaultextension=f"{ext}", filetypes=[(f"{mime} files", f"{ext}")], initialfile=name)
    if not saveAsDestination:
        return
    base, extension = os.path.splitext(saveAsDestination)
    if extension != ext:
        saveAsDestination = base + ext
    engine.sendFileAccept(id, name, saveAsDestination, size, path)
    activateFileItem(id)

def cancelTransfer(id):
    for item in fileItems:
        if item[1]["id"] == id:
            item[1]["type"] = "cancelFile"
    engine.sendCloseFileGUI(id)
    clearTab(fileWidgets)
    constructFileTab()

def closeItem(id):
    removeFileItem(id)
    clearTab(fileWidgets)
    constructFileTab()

def constructFileTab():
    global fileWidgets, fileItems
    startBtn = tkinter.Button(fileTab, text="Start file transfer", anchor="center", command=startTransfer)
    startBtn.grid(row=0, column=1)
    if len(fileItems) == 0:
        emptyLabel = tkinter.Label(fileTab, text="No file transfers have happened yet!", anchor="center")
        emptyLabel.grid(row=1, column=0, columnspan=3)
        fileWidgets[(1, 0)] = emptyLabel
    else:
        for i, item in enumerate(fileItems):
            baseRow = i * 3 + 1
            if item[1]["type"] == "transferRequest":
                typeF = "Pending Request"
                newItemLabel = tkinter.Label(fileTab, text=typeF, anchor="center")
                newItemLabel.grid(row=baseRow, column=0)
                fileWidgets[(baseRow, 0)] = newItemLabel
                name = tkinter.Label(fileTab, text=item[1]["name"], anchor="center")
                name.grid(row=baseRow, column=1)
                fileWidgets[(baseRow, 1)] = name
                mime = tkinter.Label(fileTab, text=item[1]["mime"], anchor="center")
                mime.grid(row=baseRow, column=2)
                fileWidgets[(baseRow, 2)] = mime
                if item[0]:
                    waiting = tkinter.Label(fileTab, text="Waiting for peer to accept transfer...", anchor="center")
                    waiting.grid(row=baseRow+1, column=1)
                    fileWidgets[(baseRow+1, 1)] = waiting
                    closeAction = partial(cancelTransfer, item[1]["id"])
                    close = tkinter.Button(fileTab, text="Cancel", anchor="center", command=closeAction)
                    close.grid(row=baseRow+1, column=2)
                    fileWidgets[(baseRow+1, 2)] = close
                else:
                    acceptAction = partial(acceptTransfer, item[1]["id"], item[1]["name"], item[1]["extension"], item[1]["mime"], item[1]["fileSize"], item[1]["path"])
                    acceptBtn = tkinter.Button(fileTab, text="Accept", anchor="center", command=acceptAction)
                    acceptBtn.grid(row=baseRow+1, column=0)
                    fileWidgets[(baseRow+1, 0)] = acceptBtn
                    size = tkinter.Label(fileTab, text=findHumanDataSize(item[1]["fileSize"]), anchor="center")
                    size.grid(row=baseRow+1, column=1)
                    fileWidgets[(baseRow+1, 1)] = size
                    rejectAction = partial(rejectTransfer, item[1]["id"], item[1]["name"])
                    rejectBtn = tkinter.Button(fileTab, text="Reject", anchor="center", command=rejectAction)
                    rejectBtn.grid(row=baseRow+1, column=2)
                    fileWidgets[(baseRow+1, 2)] = rejectBtn
            elif item[1]["type"] == "activeTransfer":
                label = tkinter.Label(fileTab, text="Active transfer", anchor="center")
                label.grid(row=baseRow, column=0)
                fileWidgets[(baseRow, 0)] = label
                eta = tkinter.Label(fileTab, text="0 seconds", anchor="center")
                eta.grid(row=baseRow, column=1)
                fileWidgets[(baseRow, 1)] = eta
                speed = tkinter.Label(fileTab, text="0 KB/S", anchor="center")
                speed.grid(row=baseRow, column=2)
                fileWidgets[(baseRow, 2)] = speed
                proggisBar = ttk.Progressbar(fileTab, orient="horizontal", mode="determinate")
                proggisBar.grid(row=baseRow+1, column=0, columnspan=3, sticky="ew")
                fileWidgets[(baseRow+1, 0)] = proggisBar
            elif item[1]["type"] in ("rejFile", "doneFile", "cancelFile"):
                typeF = ""
                if item[1]["type"] == "rejFile":
                    typeF = "Transfer Rejected!"
                elif item[1]["type"] == "cancelFile":
                    typeF = "Transfer Cancelled!"
                newItemLabel = tkinter.Label(fileTab, text=typeF, anchor="center")
                newItemLabel.grid(row=baseRow, column=0)
                fileWidgets[(baseRow, 0)] = newItemLabel
                name = tkinter.Label(fileTab, text=item[1]["name"], anchor="center")
                name.grid(row=baseRow, column=1)
                fileWidgets[(baseRow, 1)] = name
                mime = tkinter.Label(fileTab, text=item[1]["mime"], anchor="center")
                mime.grid(row=baseRow, column=2)
                fileWidgets[(baseRow, 2)] = mime
                okAction = partial(closeItem, item[1]["id"])
                okBtn = tkinter.Button(fileTab, text="Close", anchor="center", command=okAction)
                okBtn.grid(row=baseRow+1, column=1)
                fileWidgets[(baseRow+1, 1)] = okBtn
            placeHolder = tkinter.Label(fileTab, text="******", anchor="center")
            placeHolder.grid(row=baseRow+2, column=1)
            fileWidgets[(baseRow+2, 1)] = placeHolder

if __name__ == "__main__":
    engine.writeIdentityKeysGUI()
    setup()
    # constructTestTab()
    constructSettingsTab()
    constructChatTab()
    constructContactsTab()
    constructFileTab()
    constructAccountTab()
    atexit.register(engine.closeConnectionGUI)
    readQueue()
    window.mainloop()