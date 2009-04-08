from agent import Agent
from pandac.PandaModules import CollisionRay
from pandac.PandaModules import CollisionSphere
from pandac.PandaModules import CollisionNode
from pandac.PandaModules import CollisionTraverser
from pandac.PandaModules import CollisionHandlerQueue
from pandac.PandaModules import Vec3
from pandac.PandaModules import Vec2
from pandac.PandaModules import BitMask32
from pandac.PandaModules import LineSegs
from pandac.PandaModules import NodePath
from pandac.PandaModules import TextNode
from direct.task import Task
from direct.gui.OnscreenText import OnscreenText
##from neat import config, population, chromosome, genome, visualize
##from neat.nn import nn_pure as nn
##from neat.config import Config
import random
import math
from math import sqrt
from waypoint import Waypoint
from pathFinder import PathFinder
from tasktimer import taskTimer
        
def RandGenerator():
    while True:
        random.seed()
        yield random.uniform(-1000, 1000)
        
RG = RandGenerator()


# needed for neat-python
##config.load('ai_config')
        
class NPC(Agent):
    collisionCount = 0
    npcState = None
    def __init__(self, 
                modelStanding, 
                modelAnimationDict, 
                turnRate, 
                speed, 
                agentList, 
                rangeFinderCount = 13,
                collisionMask=BitMask32.allOff(),
                adjacencySensorThreshold = 0,
                radarSlices = 0,
                radarLength = 0.0,
                scale = 1.0,
                brain = None,
                massKg = 0.1,
                collisionTraverser = None,
                waypoints = None):
        Agent.__init__(self, modelStanding, modelAnimationDict, turnRate, speed, agentList, massKg, collisionMask, collisionTraverser)
        self.collisionMask = collisionMask
        self.adjacencySensorThreshold = adjacencySensorThreshold
        self.radarSlices = radarSlices
        self.radarLength = radarLength
        self.scale = scale
        self.brain = brain
        self.npcState = "wander"
        self.waypoints = waypoints
##        if None == self.brain:
##            self.brain = chromosome.Chromosome.create_fully_connected()
##            if Config.hidden_nodes > 0:
##                self.brain.add_hidden_nodes(Config.hidden_nodes)
        
        self.setScale(self.scale)
        self.rangeFinderCount = rangeFinderCount
        self.rangeFinders = [CollisionRay() for i in range(self.rangeFinderCount)]
        self.persistentRangeFinderData = {}
        self.currentTarget = None
        self.player = None
        self.bestPath = None
        self.key = NodePath("Room1Key")#Location that key is supposed to be
        self.key.setPos(Vec3(0, 0, 0))
        for rangeFinder in self.rangeFinders:
            self.persistentRangeFinderData[rangeFinder] = 0
            
                    
        self.annMovementRequests = {
            "left":False,
            "right":False,
            "up":False,
            "down":False}
        
        # Set up the range finders                            
        rangeFinderCollisionNode = CollisionNode("rangeFinders")
        deviation = 180 / (self.rangeFinderCount-1)
        angle = 0
        for rangeFinder in self.rangeFinders:
            rangeFinder.setOrigin(self.getX(), self.getY(), self.getZ() + 3.5)
            
            rangeFinder.setDirection(math.cos(math.radians(angle)),
                                    -math.sin(math.radians(angle)),
                                    0)
            
            rangeFinderCollisionNode.addSolid(rangeFinder)

            # Set the Collision mask
            rangeFinderCollisionNode.setFromCollideMask(self.collisionMask)
            rangeFinderCollisionNode.setIntoCollideMask(BitMask32.allOff())
            
            angle += deviation
            
        rangeFinderCollisionNodePath = self.attachNewNode(rangeFinderCollisionNode)
        # Uncomment the following line to show the collision rays
##        rangeFinderCollisionNodePath.show()
        
        # Create the CollisionTraverser and the CollisionHandlerQueue
        self.traverser = CollisionTraverser()
        self.queue = CollisionHandlerQueue()
        
        self.traverser.addCollider(rangeFinderCollisionNodePath, self.queue)
        # Uncomment the following line to show the collisions
##        self.traverser.showCollisions(render)

        self.adjacentAgents = []

        # Set up visualizations for radar
        ls = LineSegs()
        ls.setThickness(2.0)
        relativeRadarLength = float(self.radarLength) / self.scale
        ls.setColor(0, 0, 1, 1)
##        for i in range(radarSlices):
##            ls.moveTo(0, 0, 0)            
##            ls.drawTo(relativeRadarLength * math.cos(float(i) * 2. * math.pi / float(radarSlices)), 
##                      relativeRadarLength * math.sin(float(i) * 2. * math.pi / float(radarSlices)), 0)
##            np = NodePath(ls.create())
##            np.reparentTo(self)
            
        # Draw a circle around NPC
##        circleResolution = 100
##        for i in range(circleResolution):
##            ls.drawTo(relativeRadarLength * math.cos(float(i) * 2. * math.pi / float(circleResolution)), 
##                        relativeRadarLength * math.sin(float(i) * 2. * math.pi / float(circleResolution)), 0)
##            ls.drawTo(relativeRadarLength * math.cos(float(i+1.) * 2. * math.pi / float(circleResolution)), 
##                        relativeRadarLength * math.sin(float(i+1.) * 2. * math.pi / float(circleResolution)), 0)
##            np = NodePath(ls.create())
##            np.reparentTo(self)        

    def sense(self, task):
        self.rangeFinderSense()
        self.adjacencySense()
        self.radarSense()
        return Task.cont
    
    def think(self, task):
#        self.ANNThink()
        self.bestPath = PathFinder.AStar(self.__room1NPC, self.__mainAgent, self.waypoints)
        if self.bestPath != None:
            ls = LineSegs()
            ls.setThickness(10.0)
            for i in range(len(self.bestPath) - 1):
                ls.setColor(0,0,1,1)
                ls.moveTo(self.bestPath[i].getPos())
                ls.drawTo(self.bestPath[i+1].getPos())
                np = NodePath(ls.create("aoeu"))
                np.reparentTo(render)
        return Task.cont
    
    isMoving = False
    def act(self, task):
        
##        if self.currentTarget:
##            self.seek(self.currentTarget.getPos())
        #print("Called act")
        self.followPath()
        if self.npcState == "wander":
            self.wander()
            if self.player != None:
                #print("distanceToPlayer = " + str(self.distanceToPlayer()) + " radarLength = " + str(self.radarLength))
                if self.distanceToPlayer() < self.radarLength:
                    #print("Changeing from wander to seek")
                    #self.npcState = "seek"
                    #self.currentTarget = self.player
                    #self.bestPath = [self.player]
                    self.handleTransition("withinRange")
        if self.npcState == "seek":
            #print("Seeking")
            if self.currentTarget:
                #print("Valid current Target")
                self.seek(self.currentTarget.getPos())
            if self.distanceToPlayer() > self.radarLength:
                #self.npcState = "wander"
                self.handleTransition("outOfRange")
        if self.npcState == "retriveKey":
            if self.currentTarget:
                self.seek(self.currentTarget.getPos())
            if self.distanceToPlayer() < 3:#If collided with Player
                self.handleTransition("gotKey")
        if self.npcState == "returnKey":
            if self.currentTarget:
                self.seek(self.currentTarget.getPos())
            offesetFromKey = self.key.getPos() - self.getPos()
            print("Distance from key = " + str(offesetFromKey.length()))
            if offesetFromKey.length() < 3:
                self.handleTransition("keyReturned")
        return Task.cont
    
    rangeFinderText = OnscreenText(text="", style=1, fg=(1,1,1,1),
                       pos=(-1.3,0.95), align=TextNode.ALeft, scale = .05, mayChange = True)

    def setPlayer(self, player):
        self.player = player
        
    def handleTransition(self, transition):
        if(self.npcState == "wander"):
            if(transition == "keyTaken"):
                print("Changing from wander to retriveKey")
                self.bestPath = PathFinder.AStar(self, self.player, self.waypoints)
                if self.bestPath != None:
                    ls = LineSegs()
                    ls.setThickness(10.0)
                    for i in range(len(self.bestPath) - 1):
                        ls.setColor(0,0,1,1)
                        ls.moveTo(self.bestPath[i].getPos())
                        ls.drawTo(self.bestPath[i+1].getPos())
                        np = NodePath(ls.create("aoeu"))
                        np.reparentTo(render)
                print("Changing from wander to seek with AStar")
                self.npcState = "retriveKey"
            elif(transition == "withinRange"):
                print("Changing from wander to Seek")
                print("NPC position = " + str(self.getPos()))
                print("player position = " + str(self.player.getPos()))
                self.bestPath = [self.player]
                self.npcState = "seek"
            else:
                print(transition + " is an undefined transition from " + self.npcState)
        elif(self.npcState == "retriveKey"):
            if(transition == "leftRoom"):
                print("Changing from retrive key to wander due to player leaving")
                self.npcState = "wander"
            elif(transition == "gotKey"):
                print("Changing from gotKey to returnKey")
                self.bestPath = PathFinder.AStar(self, self.key, self.waypoints)
                if self.bestPath != None:
                    ls = LineSegs()
                    ls.setThickness(10.0)
                    for i in range(len(self.bestPath) - 1):
                        ls.setColor(0,0,1,1)
                        ls.moveTo(self.bestPath[i].getPos())
                        ls.drawTo(self.bestPath[i+1].getPos())
                        np = NodePath(ls.create("aoeu"))
                        np.reparentTo(render)
                self.npcState = "returnKey"
            else:
                print(transition + " is an undefined transition from " + self.npcState)
        elif(self.npcState == "seek"):
            if(transition == "outOfRange"):
                print("Changing from seek to wander")
                self.npcState = "wander"
            elif(transition == "leftRoom"):
                self.npcState = "wander"
            elif(transition  == "keyTaken"):
                self.bestPath = PathFinder.AStar(self, self.player, self.waypoints)
                if self.bestPath != None:
                    ls = LineSegs()
                    ls.setThickness(10.0)
                    for i in range(len(self.bestPath) - 1):
                        ls.setColor(0,0,1,1)
                        ls.moveTo(self.bestPath[i].getPos())
                        ls.drawTo(self.bestPath[i+1].getPos())
                        np = NodePath(ls.create("aoeu"))
                        np.reparentTo(render)
            else:
                print(transition + " is an undefined transition from " + self.npcState)
        elif(self.npcState == "returnKey"):
            if(transition == "keyReturned"):
                print("Changeing from returnKey to wander due to a keyReturn")
                self.npcState = "wander"
            else:
                print(transition + " is an undefined transition from " + self.npcState)
                
    def manageState():
        if(npcState == "wander"):
            self.wander()
            if(distanceToPlayer() < radarLength):
                changeState("withinRange")
            elif(ralphTookKey):
                changeState("keyTaken")
        if(npcState == "retriveKey"):
            None
                
    def distanceToPlayer(self):
        ownPosition = self.getPos()
        #TODO: Make sure there is always
        if self.player != None:
            playerPosition = self.player.getPos()
        
        vectorToPlayer = playerPosition - ownPosition
        return vectorToPlayer.length()
    
    def rangeFinderSense(self):
        self.traverser.traverse(render)
        for rangeFinder in self.rangeFinders:
            self.persistentRangeFinderData[rangeFinder] = 0
        for i in range(self.queue.getNumEntries()):
            entry = self.queue.getEntry(i)
            point = entry.getSurfacePoint(self)
            length = point.length()
            self.persistentRangeFinderData[entry.getFrom()] = length

        pd = []
        for i in range(self.rangeFinderCount):
            pd.append(int(self.persistentRangeFinderData[self.rangeFinders[i]]))

##        self.rangeFinderText.setText("Range Data (feelers): " + str(pd))
        return
    
    adjacencyText = OnscreenText(text="", style=1, fg=(1,1,1,1),
                                 pos=(-1.3,0.90), align=TextNode.ALeft, scale = .05, mayChange = True)

    adjacencyTexts = {}
    def adjacencySense(self):
        # loop thru the positionDictionary
        index = 0
        for agent in self.agentList:
            if not self.adjacencyTexts.has_key(agent):
                self.adjacencyTexts[agent] = OnscreenText(text="", style=1, fg=(1,1,1,1),
                        pos=(-1.3,-0.85 + (index*0.05)), align=TextNode.ALeft, scale = .05, mayChange = True)
                index += 1
        index = 0
        for agent in self.agentList:
            if self != agent:
                transform = self.getPos() - agent.getPos()
                distance = transform.length()
                self.adjacencyTexts[agent].clearText()
                if distance <= self.adjacencySensorThreshold:
                    if agent not in self.adjacentAgents:
                        self.adjacentAgents.append(agent)
                    self.adjacencyTexts[agent].setText("Agent " + str(index) + ": (" + 
                            str(agent.getPos().getX()) + ", " +
                            str(agent.getPos().getY()) + ") at heading " + 
                            str(agent.getH()))
                else:   
                    if agent in self.adjacentAgents:
                        self.adjacentAgents.remove(agent)
            index += 1
        
        self.adjacencyText.setText("Adjacent Agents: " + str(len(self.adjacentAgents)))
        return
    
    radarText = OnscreenText(text="", style=1, fg=(1,1,1,1),
                             pos=(-1.3,0.85), align=TextNode.ALeft, scale = .05, mayChange = True)
##    angleText = OnscreenText(text="", style=1, fg=(1,1,1,1),
##                             pos=(-1.3,0.80), align=TextNode.ALeft, scale = .05, mayChange = True)
##    transformAngleText = OnscreenText(text="", style=1, fg=(1,1,1,1),
##                             pos=(-1.3,0.75), align=TextNode.ALeft, scale = .05, mayChange = True)
##    getHText = OnscreenText(text="", style=1, fg=(1,1,1,1),
##                             pos=(-1.3,0.70), align=TextNode.ALeft, scale = .05, mayChange = True)
    def radarSense(self):
        self.radarActivationLevels = [0] * self.radarSlices
        for agent in self.agentList:
            if self != agent:        

                transform = agent.getPos() - self.getPos()
                if transform.length() > self.radarLength:
                    continue
                # Handle the special case
                if transform.getX() == 0:
                    if transform.getY() < 0:
                        transformAngle = 3. * math.pi / 2
                    else:
                        transformAngle = math.pi / 2
                else:
                    transformAngle = math.atan2(transform.getY(), transform.getX())
                        
            
##                self.transformAngleText.setText("transformAngle = " + str(math.degrees(transformAngle)))
##                self.getHText.setText("self.getH() = " + str(self.getH()))
                
                transformAngle -= math.radians(self.getH())
                while transformAngle >= 2. * math.pi:
                    transformAngle -= (2. * math.pi)
                while transformAngle < 0.0:
                    transformAngle += (2. * math.pi)
                
##                self.angleText.clearText()
##                self.angleText.setText(str(math.degrees(transformAngle)))
                    
                orthant = int(self.radarSlices * transformAngle / (2. * math.pi))
                orthant = self.radarSlices - orthant - 1
                    
                self.radarActivationLevels[orthant] += 1
            
##        self.radarText.setText("Radar (Pie Slice): " + str(self.radarActivationLevels))
        return

    @classmethod
    def RandomClamped(self):
        r = float(RG.next())
        r /= 1000
        return r
            
    wanderTarget = Vec2(0.0, 0.0)
    callCount = 0
    def wander(self):
        self.callCount += 1
        wanderCircleRadius = 2.5
        if self.callCount == 5:
            jitter = 50.
            self.wanderTarget += Vec2(
                self.RandomClamped() * jitter, 
                self.RandomClamped() * jitter)
            self.wanderTarget.normalize()
            self.wanderTarget *= wanderCircleRadius
            self.callCount = 0
        
        # Now move the circle in front of us
        # First grab the absolute coordinates. We want to move it 'up' wanderDistance
        wanderDistance = 5.0
        theta = math.atan2(self.wanderTarget.getY(),self.wanderTarget.getX())
        relativeX = (wanderCircleRadius * math.cos(theta))
        relativeY = (wanderCircleRadius * math.sin(theta)) - wanderDistance
        targetLocal = Vec2(relativeX, relativeY)        
        distance = self.speed * taskTimer.elapsedTime
        turnAngle = self.turnRate * taskTimer.elapsedTime
        
        # Now we have a relative target. We should go there.
        heading = math.atan2(targetLocal.getY(), targetLocal.getX())
        degreesHeading = math.degrees(heading)
        if -90.0 < degreesHeading and degreesHeading <= 0.0:
            self.turnLeft(turnAngle)
        else:
            self.turnRight(turnAngle)
        
        self.moveForward(distance)
        
        # He's always going to be moving, so let's make him loop the animation.
        if not self.isMoving:
            self.loop("run")
            self.isMoving = True
        return    


    
    generationLifetimeTicks = 500
    ANNThinkCallCount = 500
    def ANNThink(self):
        """ 
        This method is called by the think task to implement an ANN using
        neat-python. Its inputs are the radar activation levels and its
        outputs are movement requests. We are NOT evaluating the fitness
        in this function. Rather, we just use our brain.
        """        
        self.ANNThinkCallCount += 1
        annInputs = [self.getX(), self.getY()]
        annInputs.extend(self.radarActivationLevels)
        annInputs.extend(self.persistentRangeFinderData.values())
        phenotype = nn.create_phenotype(self.brain)
        outputs = phenotype.pactivate(annInputs) # parallel activation
        
##        print(outputs)
                    
        self.annMovementRequests["left"]    = (outputs[0] > 0.5)
        self.annMovementRequests["right"]   = (outputs[1] > 0.5)
        self.annMovementRequests["up"]      = (outputs[2] > 0.5)
        self.annMovementRequests["down"]    = (outputs[3] > 0.5)
    
    def ANNAct(self):
        """
        This method acts upon the movement requests that were calculated in ANNThink.
        """
        turnAngle = self.turnRate * taskTimer.elapsedTime
        distance = self.speed * taskTimer.elapsedTime
        
        if self.annMovementRequests["left"]:
            self.turnLeft(turnAngle)
        if self.annMovementRequests["right"]:
            self.turnRight(turnAngle)
        if self.annMovementRequests["up"]:
            self.moveForward(distance)
        if self.annMovementRequests["down"]:
            self.moveBackward(distance)
            
        if self.annMovementRequests["left"] or \
            self.annMovementRequests["right"] or \
            self.annMovementRequests["up"] or \
            self.annMovementRequests["down"]:
            if not self.isMoving:
                self.loop("run")
                self.isMoving = True
        else:
            self.stop()
            self.pose("walk", frame = 5)
            self.isMoving = False

                
    def seekTarget(self, seekTarget):
        moveDistance = self.speed * taskTimer.elapsedTime
        moveAngle = self.turnRate * taskTimer.elapsedTime
        
        oldHeadingDegrees = self.getH()
        self.lookAt(seekTarget)
        newHeadingDegrees = self.getH()
        self.setH(oldHeadingDegrees)
        
        oldHeadingDegrees %= 360.0
        newHeadingDegrees += 180.0
        newHeadingDegrees %= 360.0
        
        deltaHeadingDegrees = math.fabs(oldHeadingDegrees - newHeadingDegrees)
        negSwitch = deltaHeadingDegrees < 180.0 and 1.0 or -1.0
        if oldHeadingDegrees < newHeadingDegrees:
            self.turnLeft(negSwitch * moveAngle)
        if oldHeadingDegrees > newHeadingDegrees:
            self.turnRight(negSwitch * moveAngle)
        
        deltaR = math.hypot(self.getX()-seekTarget.getX(), self.getY() - seekTarget.getY())
        if deltaR > self.radarLength:
            self.moveForward(moveDistance)
            
        if math.fabs(oldHeadingDegrees - newHeadingDegrees) < 2*moveAngle and deltaR < self.radarLength:
            if self.isMoving:
                self.stop()
                self.pose("walk", frame = 5)
                self.isMoving = False
        else:
            if not self.isMoving:
                self.loop("run")
                self.isMoving = True
            
            
        return Task.cont
    
    def followPath(self):
        #If there are any waypoints in the path
        #print("Attempting to follow path")
        if self.bestPath:
            self.currentTarget = self.bestPath[0]
            #if the next waypoint is reached
            if PathFinder.distance(self, self.currentTarget) < 2: #This number must be greater than distance in seek()
                self.bestPath.pop(0)
        return Task.cont

    def seek(self, position):
        #print("Seeking position " + str(position.getX()) + ", " + str(position.getY()))
        #print("Current position " + str(self.getX())     + ", " + str(position.getY()))
        worldPosition = self.getPos()
        worldTargetPosition = position
        worldHeading = self.getH()
        worldHeading = worldHeading % 360
        worldYDirection = worldTargetPosition.getY() - worldPosition.getY()
        worldXDirection = worldTargetPosition.getX() - worldPosition.getX()
        worldDirectionToTarget = math.degrees(math.atan2(worldYDirection, worldXDirection))
        distanceToTarget = math.sqrt(worldYDirection * worldYDirection + worldXDirection * worldXDirection)
        #print("distanceToTarget = " + str(distanceToTarget))
        angleToTarget = worldDirectionToTarget - worldHeading + 180
        angleToTarget = angleToTarget % 360
        turnAngle = self.turnRate * taskTimer.elapsedTime
        distance = self.speed * taskTimer.elapsedTime
        #To limit seek range, check against self.radarLength
        if(0 < distanceToTarget):
            #print("Target is in range")
            if not self.isMoving:
                self.loop("run")
                self.isMoving = True
            if(45 <= angleToTarget <= 135):
                self.moveForward(distance)
            if(0 <= angleToTarget < 90):
                #self.moveForward(0)#do nothing
                #self.moveForward(distance)
                #self.turnLeft(turnAngle)
                self.turnRight(turnAngle)
            elif(90 <= angleToTarget < 180):
                #self.moveForward(0)#do nothing
                #self.moveForward(distance)
                self.turnLeft(turnAngle)
                #self.turnRight(turnAngle)
            elif(180 <= angleToTarget < 270):
                self.moveForward(0)#do nothing
                #self.moveForward(distance)
                self.turnLeft(turnAngle)
                #self.turnRight(turnAngle)
            elif(270 <= angleToTarget < 360):
                self.moveForward(0)#do nothing
                #self.moveForward(distance)
                #self.turnLeft(turnAngle)
                self.turnRight(turnAngle)
            #else:
            #    print("You can start crying now.")
        else:
            if self.isMoving:
                self.stop()
                self.pose("walk", 5)
                self.isMoving = False
            #print("Target is out of range")
        return

if __name__ == "__main__":
    N = NPC("models/ralph",
            {"run":"models/ralph-run"},
            turnRate = 5,
            speed = 100,
            agentList = [])
    print ("compiled good")
    
