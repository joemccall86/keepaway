from agent import Agent
from pandac.PandaModules import NodePath
from pandac.PandaModules import BitMask32
from direct.task import Task
from tasktimer import taskTimer
from direct.showbase.DirectObject import DirectObject

class Player(Agent, DirectObject):
    def __init__(self, 
                modelStanding, 
                modelAnimationDict, 
                turnRate, 
                speed, 
                agentList,
                name = "",
                massKg = 0.1,
                collisionMask = BitMask32.allOff(),
                scale = 1.0,
                collisionHandler = None,
                collisionTraverser = None):
        Agent.__init__(self, modelStanding, modelAnimationDict, turnRate, speed, agentList, massKg, collisionMask, name, collisionHandler, collisionTraverser)
        self.rightHand = self.actor.exposeJoint(None, 'modelRoot', 'RightHand')
        self.currentKey = None

        #Camera position stuff
        self.pitch = 0;
        self.heading = 0;
        self.last = 0;
        self.mousex = 0
        self.mousey = 0
            
    playerKeys = []
    
    def setCurrentKey(self, key):
        if self.currentKey:
            self.currentKey.detachNode()
        if key:
            key.reparentTo(self.rightHand)
        self.currentKey = key
    
    def addKey(self, key):
        self.playerKeys.append(key)
    
    def hasKey(self, key):
        return key in self.playerKeys
    
    def removeKey(self, key):
        assert(key in self.playerKeys)
        if key in self.playerKeys:
            self.playerKeys.remove(key)
    
    
    __inputMap = {"left":False,
            "right":False,
            "up":False,
            "down":False,
            "createBlock":False,
            "deleteBlock":False}
    
    waypointPositions = []
    def setKeymap(self):
        
        wpFile = open("waypoints.txt", "w")
        def dropWp():
            torus = loader.loadModel("models/Torus/Torus")
            torus.reparentTo(render)
            torus.setPos(self.getPos())
            self.waypointPositions.append(torus.getPos())
            wpFile.write(str((int(self.getX()), int(self.getY()))) + "\r\n")
        
        self.accept("space", dropWp)
        
        def setKey(key, value):
            self.__inputMap[key] = value
        
        self.accept("arrow_left",     setKey, ["left", True])
        self.accept("arrow_left-up",  setKey, ["left", False])
        self.accept("arrow_right",    setKey, ["right", True])
        self.accept("arrow_right-up", setKey, ["right", False])
        self.accept("arrow_up",       setKey, ["up", True])
        self.accept("arrow_up-up",    setKey, ["up", False])
        self.accept("arrow_down",     setKey, ["down", True])
        self.accept("arrow_down-up",  setKey, ["down", False])
        
        self.accept("mouse1",         setKey, ["createBlock", True])
        self.accept("mouse1-up",      setKey, ["createBlock", False])
        self.accept("mouse3",         setKey, ["deleteBlock", True])
        self.accept("mouse3-up",      setKey, ["deleteBlock", False])
    

    

    def cameraPosition(self, task):        
        base.camera.reparentTo(self)
        base.camera.setPos(0, 20, 10)
        #base.camera.lookAt(self.__mainAgent)
        #base.camera.setP(base.camera.getP() + 10)
        
        # figure out how much the mouse has moved (in pixels)
        md = base.win.getPointer(0)
        x = md.getX()
        y = md.getY()
        if base.win.movePointer(0, 100, 100):
            self.heading = self.heading - (x - 100)
            self.pitch = self.pitch - (y - 100)
            
        if (self.pitch < -90): self.pitch = -90
        if (self.pitch >  45): self.pitch =  45
        self.setH(self.heading-180)
        base.camera.lookAt(self)
        base.camera.setP(base.camera.getP() + 20)
        #base.camera.setHpr(self.heading,self.pitch,0)
        #dir = base.camera.getMat().getRow3(1)
        elapsed = task.time - self.last
        if (self.last == 0): elapsed = 0
        #if (self.mousebtn[0]):
        #    self.focus = self.focus + dir * elapsed*30
        #if (self.mousebtn[1]) or (self.mousebtn[2]):
        #    self.focus = self.focus - dir * elapsed*30
        #base.camera.setPos(self.focus - (dir*5))
        #if (base.camera.getX() < -59.0): base.camera.setX(-59)
        #if (base.camera.getX() >  59.0): base.camera.setX( 59)
        #if (base.camera.getY() < -59.0): base.camera.setY(-59)
        #if (base.camera.getY() >  59.0): base.camera.setY( 59)
        #if (base.camera.getZ() <   5.0): base.camera.setZ(  5)
        #if (base.camera.getZ() >  45.0): base.camera.setZ( 45)
        #self.focus = base.camera.getPos() + (dir*5)
        self.last = task.time
        return Task.cont
    
    
    lastMouse1State = False
    lastMouse3State = False
    def processKey(self, task):
        
        turnAngle = self.turnRate * taskTimer.elapsedTime
        distance = self.speed * taskTimer.elapsedTime
        
        self.previousPosition = self.getPos()
        
        if self.__inputMap["left"]:
            self.turnLeft(turnAngle)
        if self.__inputMap["right"]:
            self.turnRight(turnAngle)
        if self.__inputMap["up"]:
            self.moveForward(distance)
        if self.__inputMap["down"]:
            self.moveBackward(distance)
        
        if self.__inputMap["createBlock"] and self.lastMouse1State == False:
            self.createBlock(0,0,0);
            self.lastMouse1State = True
        elif not self.__inputMap["createBlock"]:
            self.lastMouse1State = False

        if self.__inputMap["deleteBlock"] and self.lastMouse3State == False:
            self.deleteBlock(0,0,0)
            self.lastMouse3State = True
        elif not self.__inputMap["deleteBlock"]:
            self.lastMouse3State = False
        
            
        if self.__inputMap["left"] or \
            self.__inputMap["right"] or \
            self.__inputMap["up"] or \
            self.__inputMap["down"]:
            if not self.isMoving:
                self.loop("run")
                self.isMoving = True
        else:
            self.stop()
            self.pose("walk", frame = 5)
            self.isMoving = False
        
        # Store the previous time and continue
        self.__previousTime = task.time
        return Task.cont
    
if __name__ == "__main__":
    print ("compiled")
    
