import math
import random

random.seed(a=None)

a = {}
for i in range(1,50000):
	a[i] = random.choice([1,0,-1,-1,-1])

positivevotes = 0
negativevotes = 0
for k in a:
	i = a[k]
	if i == -1:
		negativevotes = negativevotes + 1
	elif i == 1:
		positivevotes = positivevotes + 1
print "Total negative " + str(negativevotes)
print "Total positive " + str(positivevotes)
print "Possy " + str((10 * (1 + math.log10(positivevotes))))
print "Neggy " + str((9 * (1 + math.log10(negativevotes))))
score = 0 + (10 * (1 + math.log10(positivevotes))) - (5 * (1 + math.log10(negativevotes)))
print "Score " + str(score)
