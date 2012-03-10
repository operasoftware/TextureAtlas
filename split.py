import sys
import os
import Image
import ImageDraw
import math

w = 5
h = 4
src = Image.open('Brownie_escaperight.png')
src = src.convert('RGBA')
for y in range(h):
  for x in range(w):
    img = src.crop([x * (src.size[0]/w), y * (src.size[1]/h), (x + 1) * (src.size[0]/w), (y + 1) * src.size[1]/h])
    img.load()
    img.save('escaperight'+str(y*w+x)+'.png');
