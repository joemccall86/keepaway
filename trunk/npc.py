from agent import Agent
from pandac.PandaModules import CollisionRay
from pandac.PandaModules import CollisionNode
from pandac.PandaModules import CollisionTraverser
from pandac.PandaModules import CollisionHandlerQueue
from pandac.PandaModules import Vec3
from pandac.PandaModules import BitMask32
from pandac.PandaModules import LineSegs
from pandac.PandaModules import NodePath
from pandac.PandaModules import TextNode
from direct.task import Task
from direct.gui.OnscreenText import OnscreenText
import math

class NPC(Agent):
    collisionCount = 0
    
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
                scale = 1.0):
        Agent.__init__(self, modelStanding, modelAnimationDict, turnRate, speed, agentList)
        self.collisionMask = collisionMask
        self.adjacencySensorThreshold = adjacencySensorThreshold
        self.radarSlices = radarSlices
        self.radarLength = radarLength
        self.scale = scale
        
        self.setScale(self.scale)
        
        self.rangeFinderCount = rangeFinderCount
        self.rangeFinders = [CollisionRay() for i in range(self.rangeFinderCount)]
        self.persistentRangeFinderData = {}
        for rangeFinder in self.rangeFinders:
            self.persistentRangeFinderData[rangeFinder] = 0
            
        
        
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
            rangeFinderCollisionNode.setIntoCollideMask(self.collisionMask)
            
            angle += deviation
            
        rangeFinderCollisionNodePath = self.attachNewNode(rangeFinderCollisionNode)
        # Uncomment the following line to show the collision rays
        rangeFinderCollisionNodePath.show()
        
        # Create the CollisionTraverser and the CollisionHandlerQueue
        self.traverser = CollisionTraverser()
        self.queue = CollisionHandlerQueue()
        
        self.traverser.addCollider(rangeFinderCollisionNodePath, self.queue)
        # Uncomment the following line to show the collisions
        self.traverser.showCollisions(render)

        self.adjacentAgents = []

        # Set up visualizations for radar
        ls = LineSegs()
        ls.setThickness(5.0)
        relativeRadarLength = float(self.radarLength) / self.scale
        ls.setColor(0, 0, 1, 1)
        for i in range(radarSlices):
            ls.moveTo(0, 0, 0)            
            ls.drawTo(relativeRadarLength * math.cos(float(i) * 2. * math.pi / float(radarSlices)), 
                      relativeRadarLength * math.sin(float(i) * 2. * math.pi / float(radarSlices)), 0)
            np = NodePath(ls.create())
            np.reparentTo(self)
            
        # Draw a circle around NPC
        circleResolution = 100
        for i in range(circleResolution):
            ls.drawTo(relativeRadarLength * math.cos(float(i) * 2. * math.pi / float(circleResolution)), 
                        relativeRadarLength * math.sin(float(i) * 2. * math.pi / float(circleResolution)), 0)
            ls.drawTo(relativeRadarLength * math.cos(float(i+1.) * 2. * math.pi / float(circleResolution)), 
                        relativeRadarLength * math.sin(float(i+1.) * 2. * math.pi / float(circleResolution)), 0)
            np = NodePath(ls.create())
            np.reparentTo(self)
        


    def sense(self, task):
        self.rangeFinderSense()
        self.adjacencySense()
        self.radarSense()
        return Task.cont
    
    def think(self):
        return
    
    def act(self):
        return
    
    rangeFinderText = OnscreenText(text="", style=1, fg=(1,1,1,1),
                       pos=(-1.3,0.95), align=TextNode.ALeft, scale = .05, mayChange = True)
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

        self.rangeFinderText.setText("Range Data (feelers): " + str(pd))
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
                        
##                ls = LineSegs()
##                ls.setThickness(5.0)
##                ls.moveTo(self.getPos())
##                ls.drawTo(transform.length() * math.cos(transformAngle) / self.scale, transform.length() * math.sin(transformAngle) / self.scale, 0)
##                np = NodePath(ls.create("arst"))
##                np.reparentTo(render)
            
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
            
        self.radarText.setText("Radar (Pie Slice): " + str(self.radarActivationLevels))
        return

if __name__ == "__main__":
    N = NPC("models/ralph",
            {"run":"models/ralph-run"},
            turnRate = 5,
            speed = 100,
            agentList = [])
    print ("compiled good")
    