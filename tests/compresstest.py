import pylzma,sys

initialstring = """Lorem ipsum dolor sit amet, consectetur adipiscing elit. Maecenas eu nisi velit. Nulla in ipsum vel velit dictum laoreet id nec enim. Nullam ipsum magna, consectetur ac semper in, bibendum ut elit. Suspendisse a justo nec lorem vehicula iaculis et vitae enim. Etiam adipiscing mollis ornare. Nullam enim nisi, congue non tincidunt nec, gravida eu metus. Ut iaculis fermentum lobortis. Suspendisse in pharetra leo. Nunc eleifend fringilla eros porttitor accumsan. Aenean a erat id sapien pharetra semper. Aenean sagittis accumsan metus quis scelerisque. Quisque at eros dui, id mattis ligula. Pellentesque congue nibh ornare nulla volutpat fringilla. Quisque at fringilla tortor. Donec a neque nibh. Curabitur at porttitor ipsum. Nulla at pellentesque lorem.

In hac habitasse platea dictumst. Nam adipiscing pharetra tempor. Sed eu enim tellus, at aliquam urna. Fusce in libero sapien. Integer vehicula lorem aliquet nulla blandit auctor. Morbi interdum tellus sed nunc elementum fermentum. Suspendisse a lectus sapien. Pellentesque id enim erat. Aenean scelerisque dui at sapien tristique ultricies. Aliquam blandit varius nisl quis scelerisque. Donec sit amet dui non sem euismod vulputate. Morbi vel nunc tortor.

Suspendisse eget imperdiet augue. Donec sollicitudin arcu eu augue varius a pharetra nibh laoreet. Vestibulum vehicula justo nec eros sollicitudin in malesuada ligula sodales. Ut est neque, congue et mattis vel, bibendum vel lectus. Aliquam tincidunt, velit sit amet tristique blandit, enim felis lobortis sem, eget fringilla lacus felis vel nisi. Integer mattis tincidunt risus, mattis congue ipsum iaculis et. Nulla facilisi. Donec et leo risus, at feugiat diam. Curabitur sodales condimentum justo, et cursus tortor scelerisque ut. Maecenas quis felis ut nisl aliquet pharetra sed vel nisl. Fusce consectetur, tortor sed accumsan aliquam, mauris nibh aliquam purus, eu blandit quam dolor a velit. Sed facilisis sagittis elit, in iaculis orci tincidunt eu. """

compressed = pylzma.compress(initialstring,dictionary=27,fastBytes=255)
pylzma.decompress(compressed)

print "Compressed size " + str(sys.getsizeof(compressed))
print "Full Size " + str(sys.getsizeof(initialstring))

f = open('workfile', 'w')
f.write(compressed)
f.close()

g = open('workfile', 'r')
filecontents = g.read()

uncompressed = pylzma.decompress(filecontents) 
print uncompressed
