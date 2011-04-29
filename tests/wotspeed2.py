import math
import random
import pprint
import string
import time

random.seed(a=None)
    

class user:
    def __init__(self):
        self.name = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(6))
        self.trustscores = {}
        self.trustcache = {}
    
    def gatherTrust(self,allusers,incomingtrust,askingabout):

        score = 0 #You start off Neutral
        maxtrust = .4 * incomingtrust #Max trust we can return    
        
        #Cache trust for X seconds, where X is the value in the comparator
        if self.trustcache.has_key((askingabout,incomingtrust)):
            #Only use values cached in the last second
            if time.time() - self.trustcache[askingabout,incomingtrust][1] < 20:
                return self.trustcache[askingabout,incomingtrust][0]
                
                
                
        if askingabout == self.name:
            self.trustcache[askingabout,incomingtrust] = [round(incomingtrust),time.time()]
            return round(incomingtrust)
        if incomingtrust <= 2:
            self.trustcache[askingabout,incomingtrust] = [0,time.time()]
            return 0
            #Don't recurse forever, please.


        #If we have a trust score, use it.
        if self.trustscores.has_key(askingabout):
            score = self.trustscores[askingabout]    
        else: 
            
            # If we don't have it listed, check our friends. 
            for user in self.trustscores.keys():
                specificuser = allusers[user]
            if self.trustscores[user] > 0: #Only get reports from people we trust
                score += specificuser.gatherTrust(allusers,round(maxtrust),askingabout )
    
    
    
        #Add up all the user trusts, and cap at MaxTrust
        if score > maxtrust:
            score = maxtrust
        if score < (-1 * maxtrust):
            score = (-1 * maxtrust)
        
        self.trustcache[askingabout,incomingtrust] = [round(score),time.time()]       
        return round(score)
    
    
    
starttime = time.time()
allusers = {}
testcount = 1000
testassignments = 300
messagecount = 30
ratioPostoNeg = .75

#Generate a bunch of test servers
for i in range(0,testcount):
    u = user()
    allusers[u.name] = u

#Assign the random trusts
for i in range(0,testcount):
    for j in range (0,testassignments):
        randomlytrust = random.choice(allusers.keys())
        randomlydistrust = random.choice(allusers.keys())
        
        
        #Upvote if we're higher than the ratio
        RandomNumber = random.random()
        if RandomNumber > ratioPostoNeg:
            allusers[allusers.keys()[ i ]].trustscores[randomlytrust] = -100
        else:
            allusers[allusers.keys()[ i ]].trustscores[randomlydistrust] = 100
    

# for i in range(0,testcount):
#     print allusers.keys()[i] + "::"
#     pprint.pprint(allusers[allusers.keys()[i]].trustscores)

print "Time to Randomly Generate " + str(testcount) + " users with trust: "  + str(time.time() - starttime) + " seconds"
print "--"
checkfor = random.choice(allusers.keys())


starttime = time.time()

for m in range(0,messagecount):
    for i in range(0,testcount):
            # print "Trust by user: " + allusers[allusers.keys()[i]].name + " for user: " + checkfor
            j =  allusers[allusers.keys()[i]].gatherTrust(allusers,100,checkfor)

print "Time to Randomly computer trust for  " + str(messagecount) + " messages, each checking  " + str(testcount) + " users with possible trust values "  + str(time.time() - starttime) + " seconds"
       
        