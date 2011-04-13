from server import *
from container import *
from collections import OrderedDict
#Seed the random number generator with 1024 random bytes (8192 bits)
M2Crypto.Rand.rand_seed (os.urandom (1024))

s = Server("Threepwood.savewave.com.PluricServerSettings")
s.saveconfig()

#c = Container(importfile='52dfc8ea26abc1c6a23e57b413116f17799a861e1403db5aa4b7c2d6e572c52e0f9885d0fcc4ca5c3cb92d84280c1646ace0f99dbaafefa3c189eadf5ac9cd8f.7zPluricContainer')

# c = Container(importfile='example.json')
# s.receivecontainer(c.text())

# print c.prettytext()
# print "--------"
# c.reload()

# print c.prettytext()

#u = User(username='colin',password='1234')

########### CREATE A MESSAGE #######################

u = User(filename='colin.PluricUser')
u.saveuser()
c = Container()
c.message.dict['subject'] = "This is a super awesome message"
topics = []
topics.append('ExampleTopic')
c.message.dict['topictag'] = topics
c.message.dict['body'] = """Lorem ipsum dolor sit amet, consectetur adipiscing elit. Donec et tortor sed sem ullamcorper accumsan. Pellentesque adipiscing sollicitudin ligula, tincidunt rutrum turpis ultrices quis. Morbi ac viverra risus. Morbi eget magna mi, aliquet rhoncus mi. Quisque eget turpis non ante tempus egestas. Sed rhoncus dictum semper. Etiam egestas feugiat sodales. Nunc egestas pulvinar consequat. Donec egestas, dolor et consectetur egestas, leo lacus dictum neque, in lacinia sapien dolor ac eros. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Nulla nec turpis vitae est consectetur eleifend. Aenean elit arcu, porttitor eu molestie sit amet, accumsan eu purus. Donec mattis, erat pharetra imperdiet interdum, velit ante suscipit ante, quis rhoncus augue dui non velit. Sed id lacus enim, ut porta mauris. Ut fermentum, massa ut fermentum euismod, nisl est hendrerit magna, molestie aliquam leo sapien id ipsum. Pellentesque sed justo non neque iaculis pharetra id ut nibh. Aenean mollis urna at est condimentum vestibulum. Nulla at neque risus. Aliquam erat volutpat. Suspendisse ante metus, luctus eget lacinia ac, mollis eu odio. Fusce ornare tempus sem, eget viverra turpis interdum vitae. Nam at risus velit. Ut molestie, lacus quis molestie mollis, diam sem lobortis ligula, nec dignissim velit orci id nulla. Donec pellentesque eros a lacus sodales porta. Integer malesuada, massa in rutrum dapibus, erat mauris dapibus nisi, a congue ante risus ut ligula. Praesent massa nunc, aliquet non blandit non, luctus quis ante. Duis nec dolor eu tortor placerat lobortis sed eget lectus. Donec ac quam purus. Integer adipiscing aliquet vulputate. Cras eget purus augue. Donec commodo semper est non bibendum. Phasellus posuere porta purus, sed bibendum erat feugiat quis. Praesent tristique ante eu felis pellentesque non tincidunt magna auctor. Ut eget pretium tortor. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Proin interdum fringilla bibendum. Pellentesque sed nunc justo, ac porttitor neque. Proin porttitor quam eu magna eleifend non porttitor sem sagittis. Quisque auctor arcu a augue sodales blandit. Integer laoreet pellentesque urna, nec pharetra risus sollicitudin a. Sed nec neque nibh, et molestie ligula. Vivamus ultrices mi ut nisi mollis vel malesuada nibh commodo. Donec aliquet feugiat nisl, vel varius enim hendrerit at. Curabitur id accumsan neque. Donec ac purus est, non semper sem. Nunc sit amet nisl sed sapien euismod rhoncus. Vivamus hendrerit elementum nulla, ac accumsan tellus congue sollicitudin. Cras sed dolor quam, ultricies mattis mi. Donec ut tristique libero. Morbi eget fringilla dolor. Nam aliquet, dolor vel sollicitudin porttitor, mauris arcu ornare nibh, et imperdiet eros est sit amet mi. Class aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos. Morbi rhoncus vestibulum feugiat. Nunc eu erat a justo tempor faucibus a a nisi. Nam ut nibh risus, nec aliquam ipsum. Vivamus malesuada dui vel diam fringilla eu consequat lorem dignissim. Integer lobortis hendrerit eros sit amet mattis. Quisque vitae sapien dolor, vitae fermentum purus. Maecenas tempus cursus imperdiet. Integer mollis dignissim sapien, et interdum dui hendrerit ac. Morbi vehicula volutpat quam, in consectetur neque euismod at. Aenean leo dolor, tempor sed pulvinar nec, aliquam pellentesque mauris. Sed consectetur faucibus diam nec molestie. Morbi dui lacus, fermentum id vehicula quis, eleifend pulvinar felis. Fusce lorem elit, sollicitudin quis posuere vitae, lacinia quis augue. Nunc convallis nunc vel lectus egestas vitae tristique mi fermentum. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Vivamus congue est sit amet tortor scelerisque nec hendrerit augue pretium. Nulla vel est odio. Etiam dui mi, malesuada sed hendrerit vitae, convallis sit amet orci. Morbi ut libero eget nunc eleifend pulvinar vel sed neque. Mauris semper, dolor non viverra fringilla, elit arcu consequat nisl, nec facilisis eros erat eget velit. Ut ac semper sem. Aenean viverra tristique odio sed ornare. Aenean consectetur dignissim condimentum. Morbi sit amet lacus non dolor condimentum euismod. Fusce aliquam condimentum imperdiet. Ut auctor congue quam eu condimentum"""
c.message.dict['author'] = OrderedDict()
c.message.dict['author']['from'] = u.Keys.pubkey
c.message.dict['author']['client'] = "Sample Message Generator 0.1"
print c.prettytext()

######## Process said message ###########
s.receivecontainer(c.text())

######## Read in processed container ##########
filename = c.message.hash() + ".7zPluricContainer"
print "FILENAME: " + filename
c_new = Container(filename)
print c_new.prettytext()