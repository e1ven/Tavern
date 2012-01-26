from PIL import Image
import pymongo
from gridfs import GridFS


mcon = pymongo.Connection('127.0.0.1', 27017)
mongos = mcon['test']
gfs = GridFS(mongos)

attachment = gfs.get_version(filename="e515f8bf2dd1de2e609c488431338e1f640b501875156c1290a0222894a2518f78ec01489666334490e4bc57f8f7f0eafdce375f9fb18544d8bbca024f9dbf95")

im = Image.open(attachment)
attachment.seek(0)
img_width, img_height = im.size
if ((img_width > 150) or (img_height > 150)):
    im.thumbnail((150, 150), Image.ANTIALIAS)
