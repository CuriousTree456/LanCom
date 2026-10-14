import queue
import os
guiQueue = queue.Queue()

def findAbsPath(*localPath):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), *localPath)