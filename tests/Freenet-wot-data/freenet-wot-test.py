import math
import random
import pprint
import string
import time
from collections import OrderedDict
import pprint

random.seed(a=None)
    
class WotUser:
    def __init__(self):
        self.name = ""
        self.trustscores = {}
        self.trustcache = {}
        self.identity = ""
        
    def gatherTrust(self,allusers,incomingtrust,askingabout):

        score = 0 #You start off Neutral
        maxtrust = .4 * incomingtrust #Max trust we can return    
        
        #Cache trust for X seconds, where X is the value in the comparator
        if self.trustcache.has_key((askingabout,incomingtrust)):
            #Only use values cached in the last second
            if time.time() - self.trustcache[askingabout,incomingtrust][1] < 01:
                return self.trustcache[askingabout,incomingtrust][0]
                
                
        #We trust ourselves implicitly       
        if askingabout == self.identity:
            self.trustcache[askingabout,incomingtrust] = [round(incomingtrust),time.time()]
            return round(incomingtrust)
            
            
        #Don't recurse forever, please.  
        #Stop after 4 Friends-of-Friends = 100,40,16,6,0,0,0,0,0,0,0,0,0,0,0,0 etc     
        if incomingtrust <= 2:
            self.trustcache[askingabout,incomingtrust] = [0,time.time()]
            return 0

        divideby = 1
        #If we have an explicit trust score, use it.
        if self.trustscores.has_key(askingabout):
            score = float(self.trustscores[askingabout])    
        else:       
            # If we don't have it listed, check our friends. 
            for user in self.trustscores.keys():
                specificuser = allusers[user]
                if self.trustscores[user] > 0: #Only get reports from people we trust
                    receivedtrust = specificuser.gatherTrust(allusers,round(maxtrust),askingabout )
#                     print "user trust :: " + str(self.trustscores[user])
                    # print " receivedtrust :: " + str(receivedtrust)
                    score += (float(receivedtrust) * float(self.trustscores[user]))
                    divideby += 1
                    
        #Add up the trusts from our friends, and cap at MaxTrust
        score = score / divideby
        if score > maxtrust:
            score = maxtrust
        if score < (-1 * maxtrust):
            score = (-1 * maxtrust)
        
        self.trustcache[askingabout,incomingtrust] = [round(score),time.time()]       
        return round(score)
    
#Let's start by slurping in all existing Freenet Users

fileIN = open("identities.sfs", "r")
line = fileIN.readline()

FreenetFolk = OrderedDict()
MapofUserIDs = OrderedDict()

while line:
    linesegment = line.partition('=')
    if "Identity" in linesegment[0]:
        UserNumber =  linesegment[0].split('Identity')[1].strip(' \n')
        Identity = linesegment[2].strip(' \n')
        
        if not FreenetFolk.has_key(Identity):
            FreenetFolk[Identity] = WotUser()
        FreenetFolk[Identity].identity = Identity
        MapofUserIDs[UserNumber] = Identity
        
    if "Nickname" in linesegment[0]:
        UserNumber =  linesegment[0].split('Nickname')[1].strip(' \n')
        Nickname = linesegment[2].strip(' \n')
        FreenetFolk[MapofUserIDs[UserNumber]].name = Nickname    
    line = fileIN.readline()    
fileIN.close()



#Now, let's slurp in Manually assigned Trust values

TrustRelationships = OrderedDict()

fileIN = open("trusts.sfs", "r")
line = fileIN.readline()
while line:
    linesegment = line.partition('=')
    if "Trustee" in linesegment[0]:
        TrustNumber =  linesegment[0].split('Trustee')[1].strip(' \n')
        Trustee = linesegment[2].strip(' \n')
        if not TrustRelationships.has_key(TrustNumber):
            TrustRelationships[TrustNumber] = OrderedDict()
        TrustRelationships[TrustNumber]['Trustee'] = Trustee
    if "Value" in linesegment[0]:
        TrustNumber =  linesegment[0].split('Value')[1].strip(' \n')
        TrustAmount = linesegment[2].strip(' \n')
        if not TrustRelationships.has_key(TrustNumber):
            TrustRelationships[TrustNumber] = OrderedDict()
        TrustRelationships[TrustNumber]['TrustAmount'] = TrustAmount
    if "Truster" in linesegment[0]:
        TrustNumber =  linesegment[0].split('Truster')[1].strip(' \n')
        Truster = linesegment[2].strip(' \n')
        if not TrustRelationships.has_key(TrustNumber):
            TrustRelationships[TrustNumber] = OrderedDict()
        TrustRelationships[TrustNumber]['Truster'] = Truster
    line = fileIN.readline()    
fileIN.close()


#Store all the trust relationships in our User Objects
for relation in TrustRelationships.keys():
    FreenetFolk[TrustRelationships[relation]['Truster']].trustscores[TrustRelationships[relation]['Trustee']] = TrustRelationships[relation]['TrustAmount']




#For comparison, let's slurp in the Calculated Trust Values
CalculatedTrustRelationships = OrderedDict()
CalcTrustDirect = OrderedDict()

fileIN = open("scores.sfs", "r")
line = fileIN.readline()
while line:
    linesegment = line.partition('=')
    if "Trustee" in linesegment[0]:
        TrustNumber =  linesegment[0].split('Trustee')[1].strip(' \n')
        Trustee = linesegment[2].strip(' \n')
        if not CalculatedTrustRelationships.has_key(TrustNumber):
            CalculatedTrustRelationships[TrustNumber] = OrderedDict()
        CalculatedTrustRelationships[TrustNumber]['Trustee'] = Trustee
    if "Value" in linesegment[0]:
        TrustNumber =  linesegment[0].split('Value')[1].strip(' \n')
        TrustAmount = linesegment[2].strip(' \n')
        if not CalculatedTrustRelationships.has_key(TrustNumber):
            CalculatedTrustRelationships[TrustNumber] = OrderedDict()
        CalculatedTrustRelationships[TrustNumber]['TrustAmount'] = TrustAmount
        #Store this indexed by ID as well
        if not CalcTrustDirect.has_key(CalculatedTrustRelationships[TrustNumber]['Truster']):
            CalcTrustDirect[CalculatedTrustRelationships[TrustNumber]['Truster']] = OrderedDict()
        CalcTrustDirect[CalculatedTrustRelationships[TrustNumber]['Truster']][CalculatedTrustRelationships[TrustNumber]['Trustee']] = TrustAmount
    if "Truster" in linesegment[0]:
        TrustNumber =  linesegment[0].split('Truster')[1].strip(' \n')
        Truster = linesegment[2].strip(' \n')
        if not CalculatedTrustRelationships.has_key(TrustNumber):
            CalculatedTrustRelationships[TrustNumber] = OrderedDict()
        CalculatedTrustRelationships[TrustNumber]['Truster'] = Truster
    line = fileIN.readline()    
fileIN.close()


# for i in range(0,100):
#     #Pick a random user
#     Truster = random.choice(FreenetFolk.keys())
#     Trustee = random.choice(FreenetFolk.keys())
#     
#     print "PythonCalc-- Truster : " + Truster + " Trustee : " + Trustee + " "  + str(FreenetFolk[Truster].gatherTrust(allusers=FreenetFolk,incomingtrust=100,askingabout=Trustee))
#     if CalcTrustDirect.has_key(Truster):
#         print "JavaCalc-- Truster : " + Truster + " Trustee : " + Trustee + " " + CalcTrustDirect[Truster][Trusee]
#         

for i in FreenetFolk.keys():
    for j in FreenetFolk.keys():
        #Pick a random user
        Truster = i
        Trustee = j
    
        if CalcTrustDirect.has_key(Truster):
            print "JavaCalc-- Truster : " + Truster + " Trustee : " + Trustee + " " + CalcTrustDirect[Truster][Trustee]
            print "PythonCalc-- Truster : " + Truster + " Trustee : " + Trustee + " "  + str(FreenetFolk[Truster].gatherTrust(allusers=FreenetFolk,incomingtrust=100,askingabout=Trustee))
            print 
