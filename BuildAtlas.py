import sys
import os
import Image
import ImageDraw
import math

# Configurations you need to set. Only use borders if you ever do filtering on your sprites. And then you should
# probably set it to transparent or duplicate the edges depending on your use case. Using solid red now to
# make it clear they're there.
folder = './brownie'
atlasBaseName = 'atlas'
useBorder = False
borderColor = 'red'

images = []

# A source image structure that loads the image and stores the
# extents. It will also get the destination rect in the atlas written to it.
class SourceImage:
  def __init__(self, filePath, fileName, oi):
    self.filePath = filePath
    self.fileName = fileName
    self.fullPath = filePath + '/' + fileName
    self.origIndex = oi
    # Open the image and make sure it's in RGBA mode.
    self.img = Image.open(self.fullPath)
    self.img = self.img.convert('RGBA')
    self.uncropped = Rect(0,0, self.img.size[0]-1, self.img.size[1]-1)
    # Grab the bounding box from the alpha channel.
    alpha = self.img.split()[3]
    bbox = alpha.getbbox()
    alpha = None
    # Crop it and get the new extents.
    self.img = self.img.crop(bbox)
    self.img.load()
    self.offset = (bbox[0], bbox[1])
    self.rect = Rect(0,0, self.img.size[0]-1, self.img.size[1]-1)
    if useBorder:
      self.rect.xmax += 2
      self.rect.ymax += 2


# A simple rect class using inclusive coordinates.
class Rect:
  def __init__(self, x0,y0,x1,y1):
    self.xmin = int(x0)
    self.xmax = int(x1)
    self.ymin = int(y0)
    self.ymax = int(y1)

  def width(self):
    return int(self.xmax - self.xmin + 1)

  def height(self):
    return int(self.ymax - self.ymin + 1)

# A k-d tree node containing rectangles used to tightly pack images.
class Node:
  def __init__(self):
    self.image = None
    self.rect = Rect(0,0,0,0)
    self.child0 = None
    self.child1 = None

  # Iterate the full tree and write the destination rects to the source images.
  def finalize(self):
    if self.image != None:
      self.image.destRect = self.rect
    else:
      if self.child0 != None:
        self.child0.finalize()
      if self.child1 != None:
        self.child1.finalize()

  # Insert a single rect into the tree by recursing into the children.
  def insert(self, r, img):
    if self.child0 != None or self.child1 != None:
      newNode = self.child0.insert(r, img)
      if newNode != None:
        return newNode
      return self.child1.insert(r, img)
    else:
      if self.image != None:
        return None
      if r.width() > self.rect.width() or r.height() > self.rect.height():
        return None
      if r.width() == self.rect.width() and r.height() == self.rect.height():
        self.image = img
        return self
      self.child0 = Node()
      self.child1 = Node()
      dw = self.rect.width() - r.width()
      dh = self.rect.height() - r.height()
      if dw > dh:
        self.child0.rect = Rect(self.rect.xmin, self.rect.ymin, self.rect.xmin + r.width() - 1, self.rect.ymax)
        self.child1.rect = Rect(self.rect.xmin + r.width(), self.rect.ymin, self.rect.xmax, self.rect.ymax)
      else:
        self.child0.rect = Rect(self.rect.xmin, self.rect.ymin, self.rect.xmax, self.rect.ymin + r.height() - 1)
        self.child1.rect = Rect(self.rect.xmin, self.rect.ymin + r.height(), self.rect.xmax, self.rect.ymax)
      return self.child0.insert(r,img)

# An alternate heuristic for insertion order.
def imageArea(i):
  return i.rect.width() * i.rect.height()

# The used heuristic for insertion order, inserting images with the
# largest extent (in any direction) first.
def maxExtent(i):
  return max([i.rect.width(), i.rect.height()])

# Dump out an illustrative SVG showing how the atlas is created.
def writeSVG(images, atlasW, atlasH):
  rows = math.floor(math.sqrt(len(images)))
  cols = math.ceil(len(images) / rows)
  maxImgDim = 0
  for i in images:
    maxImgDim = max([maxImgDim, images[0].rect.width(), images[0].rect.height()])
  svgRez = 1000
  colSize = svgRez / (cols + 1) - 1
  scale = colSize / maxImgDim
  svgWidth = svgRez + atlasW * scale + svgRez / 20
  svgHeight = svgRez
  if cols > rows:
    svgHeight = svgRez - colSize
  svgCenterW = svgRez + (atlasW * scale + svgRez / 20) / 2
  svgCenterH = svgHeight / 2
  out = open(atlasBaseName+'.svg', 'w')
  out.write('<?xml version="1.0"?>\n<svg width="' + str(svgWidth) + '" height="' + str(svgHeight) + '" viewBox="0 0 ' + str(svgWidth) + ' ' + str(svgHeight) + '" xmlns="http://www.w3.org/2000/svg">\n')
  dstIndex = 0
  totalTime = 20.0
  timePerStep = totalTime / len(images)
  for i in images:
    c = math.floor(i.origIndex % cols)
    r = math.floor(i.origIndex / cols)
    x = (c + 1) * colSize + c
    y = (r + 1) * colSize + r
    w = i.rect.width() * scale
    h = i.rect.height() * scale
    x = x - w / 2
    y = y - h / 2
    dx = svgCenterW - atlasW * scale / 2 + (i.img.destRect.xmin + i.img.destRect.width() / 2) * scale
    dy = svgCenterH - atlasH * scale / 2 + (i.img.destRect.ymin + i.img.destRect.height() / 2) * scale
    start = 1.0 + dstIndex * timePerStep
    fstart = 1.0 + totalTime + 1.0
    out.write('  <rect id="'+str(i.origIndex)+'" x="' + str(-w/2) + '" y="' + str(-h/2) + '" width="' + str(w) + '" height="' + str(h) + '" transform="translate(' + str(x) + ',' + str(y) + ')" stroke="#000000" fill="#4bbf67">\n')
    out.write('    <animateTransform attributeName="transform" attributeType="XML" type="translate" from="' + str(x) + ' ' + str(y) + '" to="' + str(dx) + ' ' + str(dy) + '" begin="' + str(start) + '" dur="' + str(timePerStep) + 's" additive="replace" fill="freeze"/>\n')
    out.write('  </rect>\n')
    dstIndex = dstIndex + 1
  out.write('</svg>')
  out.close()

def writeAtlas(images, atlasW, atlasH):
  atlasImg = Image.new('RGBA', [atlasW, atlasH])
  if useBorder:
    draw = ImageDraw.Draw(atlasImg)
    draw.rectangle((0, 0, atlasW, atlasH), fill=borderColor)
    for i in images:
      atlasImg.paste(i.img, [int(i.img.destRect.xmin + 1), int(i.img.destRect.ymin + 1), int(i.img.destRect.xmax), int(i.img.destRect.ymax)])
  else:
    for i in images:
      atlasImg.paste(i.img, [int(i.img.destRect.xmin), int(i.img.destRect.ymin), int(i.img.destRect.xmax + 1), int(i.img.destRect.ymax + 1)])
  atlasImg.save(atlasBaseName + '.png')
  atlasImg = None

# Remove one pixel on each side of the images before dumping the CSS and JSON info.
def removeBorders(images):
  for i in images:
    i.img.destRect.xmin += 1
    i.img.destRect.ymin += 1
    i.img.destRect.xmax -= 1
    i.img.destRect.ymax -= 1

def writeCSS(images, atlasW, atlasH):
  css = open(atlasBaseName + '.css', 'w')
  for i in images:
    css.write('div.' + i.fileName.replace('.', '-') + '\n{\n')
    css.write('  position: relative;\n')
    css.write('  padding-left: ' + str(i.offset[0]) + 'px;\n')
    css.write('  padding-top: ' + str(i.offset[1]) + 'px;\n')
    css.write('  padding-right: ' + str(i.uncropped.width() - i.img.destRect.width() - i.offset[0]) + 'px;\n')
    css.write('  padding-bottom: ' + str(i.uncropped.height() - i.img.destRect.height() - i.offset[1]) + 'px;\n')
    css.write('  width: ' + str(i.img.destRect.width()) + 'px;\n')
    css.write('  height: ' + str(i.img.destRect.height()) + 'px;\n')
    css.write('  background: url(\'' + atlasBaseName + '.png' + '\') ' + str(-i.img.destRect.xmin+i.offset[0]) + 'px ' + str(-i.img.destRect.ymin+i.offset[1]) + 'px no-repeat;\n')
    css.write('  background-clip: content-box;\n}\n\n')
  css.close()

def writeJSON(images, atlasW, atlasH):
  json = open(atlasBaseName + '.json', 'w')
  json.write('{\n  "atlas" : "' + atlasBaseName + '.png",\n  "images" : [\n');
  for i in images:
    json.write('    "' + i.fileName.replace('.', '-') + '" : {\n')
    json.write('      "rect" : [' + str(i.img.destRect.xmin) + ', ' + str(i.img.destRect.ymin) + ', ' + str(i.img.destRect.xmax) + ', ' + str(i.img.destRect.ymax) + '],\n')
    json.write('      "offset" : [' + str(i.offset[0]) + ', ' + str(i.offset[1]) + '],\n')
    json.write('      "pad": [ ' + str(i.uncropped.width() - i.img.destRect.width() - i.offset[0]) + ', ' + str(i.uncropped.height() - i.img.destRect.height() - i.offset[1]) + ']\n    }')
    if i != images[-1]:
      json.write(',')
    json.write('\n')
  json.write('  ]\n}')
  json.close()

  
# Get a list of all the files in the source folder.
dirList = os.listdir(folder);
origIndex = 0
for fileName in dirList:
  if fileName[0] == '.':
    continue
  # Create source image structs and give them a unique index.
  images.append(SourceImage(folder, fileName, origIndex))
  origIndex = origIndex + 1
  
# Sort the source images using the insert heuristic.
images.sort(None, maxExtent, True)

# Calculate the total area of all the source images and figure out a starting
# width and height to use when creating the atlas.
totalArea = 0
totalAreaUncropped = 0
for i in images:
  totalArea = totalArea + i.rect.width() * i.rect.height()
  totalAreaUncropped = totalAreaUncropped + i.uncropped.width() * i.uncropped.height()
width = math.floor(math.sqrt(totalArea))
height = math.floor(totalArea / width)

# Loop until success.
while True:
  # Set up an empty tree the size of the expected atlas.
  root = Node()
  root.rect = Rect(0,0,width,height)
  # Try to insert all the source images.
  ok = True
  for i in images:
    n = root.insert(i.rect, i.img)
    if n == None:
      ok = False
      break
  # If all source images fit break out of the loop.
  if ok:
    break

  # Increase the width or height by one and try again.
  if width > height:
    height = height + 1
  else:
    width = width + 1

# We've succeeded so write the dest rects to the source images.
root.finalize()
root = None

# Figure out the actual size of the atlas as it may not fill the entire area.
atlasW = 0
atlasH = 0
for i in images:
  atlasW = max([atlasW, i.img.destRect.xmax])
  atlasH = max([atlasH, i.img.destRect.ymax])
atlasW = int(atlasW+1)
atlasH = int(atlasH+1)
print('AtlasDimensions: ' + str(atlasW) + 'x' + str(atlasH) + '  :  ' + str(int(100.0 * (atlasW * atlasH)/totalAreaUncropped)) + '% of original')

writeAtlas(images, atlasW, atlasH)
# Remove the borders from the sizes before we dumt the CSS and JSON.
if useBorder:
  removeBorders(images)
writeCSS(images, atlasW, atlasH)
writeSVG(images, atlasW, atlasH)
writeJSON(images, atlasW, atlasH)
