# This script is used to convert the height map to a 3D model in STL format.
# a lot of logics are borrowed from https://github.com/MrCheeze/botw-tools, heightmap.py

from PIL import Image, ImageDraw
import numpy as np
from scipy.ndimage import zoom
from stl import mesh
import os

file_paths = []
for folder, _, files in os.walk('terrain'):
    if not files or not files[0].endswith('.hght'):
        continue
    file_paths.append((folder, sorted(files)))

file_paths.sort()

width = 6 * 0x200
height = 6 * 0x200

# crop off the unreachable edges
y_min = int(height / 5.75)
y_max = int(height - y_min + height / 70) # hack! a little bit more on the bottom
x_min = int(width / 12)
x_max = width - x_min
x_min += x_max // 50  # hack! a little bit less on the left

base_height = 31

img = Image.new("RGB", (x_max - x_min + 1, y_max - y_min + 1))
heights = np.zeros((y_max - y_min + 1, x_max - x_min + 1))

i = 0
for folder, files in file_paths:
    y_high = [0,0,0,1,2,1,
              1,2,2,0,0,0,
              1,1,2,2,1,2,
              3,4,3,3,4,4,
              5,5,5,3,3,4,
              4,3,4,5,5,5][i] * 0x200
    x_high = [0,1,2,0,0,1,
              2,1,2,3,4,5,
              3,4,3,4,5,5,
              0,0,1,2,1,2,
              0,1,2,3,4,3,
              4,5,5,3,4,5][i] * 0x200
    x_mid = 0
    y_mid = 0
    for file in files:
        print(file)
        f = open(folder+'/'+file, 'rb')
        for y in range(y_high + y_mid, y_high + y_mid + 0x100):
            for x in range(x_high + x_mid, x_high + x_mid + 0x100):
                val = 0
                b2 = f.read(2)
                if x_max >= x >= x_min and y_max >= y >= y_min:
                    if x < x_min * 1.3 and y_min * 2.0 < y < y_min * 2.8: # hack! carve out the midtop-left piece
                        val = 0
                    else:
                        val = int.from_bytes(b2,'little') / 256 - base_height  # remove base for normalization
                        if val < 0:
                            val = 0
                else:
                    continue
                heights[y-y_min][x-x_min] = val
                val = int(val)
                img.putpixel((x-x_min,y-y_min), (val, val, val))
        f.close()
        x_mid += 0x100
        if x_mid == 0x200:
            x_mid = 0
            y_mid += 0x100
    i += 1

# this is for reference/debug only
img.save('h2stl.png')

zoom_factor = 0.5
print(f'before zoom, h={heights.shape[0]}, w={heights.shape[1]}')

# zoom down size, otherwise the mesh will be 1GB
heights = zoom(heights, zoom_factor)
height = heights.shape[0]
width = heights.shape[1]
print(f'zoom: h={height}, w={width}')

# Create the mesh
hsize = heights.size
# the top mesh plus 4 edges
vertices = np.zeros((hsize * 2, 3))

scale_print = 255.0 / width

edge_h = -20  # added 1-2mm thickness for print

# Populate the vertices with x, y, and mapped z (height) values
for r in range(height):
    for c in range(width):
        index = r * width + c
        rs = r * scale_print
        cs = c * scale_print
        vertices[index] = [rs, cs, heights[r, c] * zoom_factor*scale_print]
        vertices[hsize + index] = [rs, cs, edge_h * zoom_factor*scale_print]

# Generate faces
faces = []

for y in range(height - 1):
    for x in range(width - 1):
        # upper face
        # Index of the top-left vertex of the pixel
        top_left = y * width + x
        top_right = top_left + 1
        bottom_left = (y + 1) * width + x
        bottom_right = bottom_left + 1
        # Triangle 1
        faces.append([top_left, bottom_left, top_right])
        # Triangle 2
        faces.append([bottom_left, bottom_right, top_right])
        # lower face, different direction to maitain counter-clockwise order
        faces.append([hsize + top_left, hsize + top_right, hsize + bottom_left])
        faces.append([hsize + bottom_left, hsize + top_right, hsize + bottom_right])


# left & right faces
for y in range(height - 1):
    # left
    lb1 = hsize + width * y
    lb2 = lb1 + width
    lt1 = y * width
    lt2 = lt1 + width
    # Triangle 1
    faces.append([lb1, lb2, lt1])
    # Triangle 2
    faces.append([lt1, lb2, lt2])
    # right
    lb1 = hsize + width * y + width - 1
    lb2 = lb1 + width
    lt1 = y * width + width - 1
    lt2 = lt1 + width
    # Triangle 1
    faces.append([lb1, lt1, lb2])
    # Triangle 2
    faces.append([lb2, lt1, lt2])

# front and back faces
for x in range(width - 1):
    # front
    lb1 = hsize + x
    lb2 = lb1 + 1
    lt1 = x
    lt2 = lt1 + 1
    # Triangle 1
    faces.append([lb1, lt1, lb2])
    # Triangle 2
    faces.append([lb2, lt1, lt2])
    # back
    lb1 = hsize + x + width * (height - 1)
    lb2 = lb1 + 1
    lt1 = x + width * (height - 1)
    lt2 = lt1 + 1
    # Triangle 1
    faces.append([lb1, lb2, lt1])
    # Triangle 2
    faces.append([lb2, lt2, lt1])

# print(f'faces={faces}')

faces = np.array(faces)

# Create the mesh
the_mesh = mesh.Mesh(np.zeros(faces.shape[0], dtype=mesh.Mesh.dtype))
for i, f in enumerate(faces):
    for j in range(3):
        the_mesh.vectors[i][j] = vertices[f[j], :]

# Save the mesh to file
the_mesh.save('h2stl.stl')

# check the mesh is fine
# print(the_mesh.check(exact=True))
