from sklearn.cluster import KMeans
from PIL import Image
import numpy as np
import csv
import matplotlib.pyplot as plt
# from skimage import color
import os

def rgb_dist(rgb1, rgb2):
    return (int(rgb1[0])-int(rgb2[0]))**2+(int(rgb1[1])-int(rgb2[1]))**2+(int(rgb1[2])-int(rgb2[2]))**2

def hex_dist(hex1, hex2):
    return rgb_dist(hex2rgb(hex1),hex2rgb(hex2))

def get_nearest_hex(rgb_hex,palette):
    #returns nearest color in hex
    dist = [hex_dist(rgb_hex, p_hex) for p_hex in palette]
    return palette[dist.index(min(dist))]

def get_nearest_rgb(rgb, palette):
    return get_nearest_hex(rgb2hex((rgb[0],rgb[1],rgb[2])), palette)

def rgb2hex(rgb):
    return ('%02x%02x%02x' % rgb).upper()

def hex2rgb(value):
    value = value.lstrip('#')
    lv = len(value)
    return tuple(int(value[i:i+lv//3], 16) for i in range(0, lv, lv//3))

def get_color(img,i,j,palette):
    #gets hex value in palette of nearest color in 8 neighboring pixels
    h,w,d = img.shape
    c1 = img[i][j]
    c1hex = rgb2hex((c1[0],c1[1],c1[2]))
    if c1hex in palette:
        return c1hex
    colors = []
    distances = []

    for a in range(-1,2):
        for b in range(-1,2):
            if (a == 0 and b == 0) or i+a < 0 or i+a >= h or j+b < 0 or j+b >= w :
                continue
            c2 = img[i+a][j+b]
            colors.append(c2)
            d = rgb_dist(c1,c2)
            distances.append(d)
    
    n_rgb = colors[distances.index(min(distances))]
    
    return get_nearest_hex(rgb2hex((n_rgb[0],n_rgb[1],n_rgb[2])),palette)

def getsegment(img,i,j,palette,visited):
    #do bfs to get image segment
    h,w,d = img.shape
    # col = get_nearest_rgb(img[i][j],palette)
    col = get_color(img,i,j,palette)

    segment = []
    q = []
    q.append((i,j))
    visited.add((i,j))
    while len(q) > 0:
        pi,pj = q.pop(0)
        segment.append((pi,pj))
        
        # if pi > 0 and (pi-1,pj) not in visited and get_nearest_rgb(img[pi-1][pj],palette) == col:
        if pi > 0 and (pi-1,pj) not in visited and get_color(img,pi-1,pj,palette) == col:
            q.append((pi-1,pj))
            visited.add((pi-1,pj))
        # if pi+1 < h and (pi+1,pj) not in visited and get_nearest_rgb(img[pi+1][pj],palette) == col:
        if pi+1 < h and (pi+1,pj) not in visited and get_color(img,pi+1,pj,palette) == col:
            q.append((pi+1,pj))
            visited.add((pi+1,pj))
        # if pj > 0 and (pi,pj-1) not in visited and get_nearest_rgb(img[pi][pj-1],palette) == col:
        if pj > 0 and (pi,pj-1) not in visited and get_color(img,pi,pj-1,palette) == col:
            q.append((pi,pj-1))
            visited.add((pi,pj-1))
        # if pj+1 < w and (pi,pj+1) not in visited and get_nearest_rgb(img[pi][pj+1],palette) == col:
        if pj+1 < w and (pi,pj+1) not in visited and get_color(img,pi,pj+1,palette) == col:
            q.append((pi,pj+1))
            visited.add((pi,pj+1))
    return segment

# matrix = pixel to segment_id
def enclosure_strengths(matrix, num_ids):
    n = len(matrix)
    m = len(matrix[0])
    dist = 2
    count = [[0 for i in range(num_ids+1)] for j in range(num_ids)] # row segment, col is neighboring segment, value is unnnormalized strength
    for i in range(-dist, n+dist):
        for j in range(-dist, m+dist):
            s = set()
            outofbounds = set()
            for dx in range(-dist, dist+1):
                for dy in range(-dist, dist+1):
                    nx, ny = i+dx, j+dy
                    if nx >= 0 and nx < n and ny >= 0 and ny < m:
                        if i >= 0 and i < n and j >= 0 and j < m:
                            if matrix[i][j] != matrix[nx][ny]:
                                s.add(matrix[nx][ny])
                        else:
                            outofbounds.add(matrix[nx][ny])
            for k in s:
                count[k][matrix[i][j]]+=1
            for k in outofbounds:
                count[k][num_ids] += 1

    # normalize
    for i in range(len(count)):
        total = sum(count[i])
        if total == 0:
            continue
        for j in range(len(count[0])):
            count[i][j] /= total
        
        count[i].pop(-1)
    
    return count

def segment_image(img, palette):
    img_cpy = img.copy()

    segments = {}
    for col in palette:
        segments[col] = []

    visited = set()
    for i in range(img.shape[0]):
        for j in range(img.shape[1]):
            if (i,j) in visited:
                continue
            rgb_hex = get_nearest_rgb(img_cpy[i][j],palette)
            seg = getsegment(img_cpy,i,j,palette,visited)
            segments[rgb_hex].append(seg)

    return segments
    
def preprocess_image(img_num):
    testimg_file = os.path.join('test_set2', str(img_num)+'.png')
    testimg = Image.open(testimg_file)
    testimg = testimg.convert('RGBA')
    testimg = np.array(testimg)

    with open(os.path.join('test_set2', 'test.csv')) as file:
        reader = csv.DictReader(file)
        palette = None
        for row in reader:
            if row['patternId'] == str(img_num):
                palette = row['palette'].strip().split(' ')
    
        if palette is None:
            print("Bad image ID")
            exit(2)
    return testimg, palette

def get_color_groups(img_num):
    img, palette = preprocess_image(img_num)
    segments = segment_image(img, palette)
    color_groups = {}

    for color in palette:
        group = np.full(img.shape, 255)
        r,g,b = hex2rgb(color)
        for segment in segments[color]:
            for px in segment:
                group[px[0]][px[1]] = [r,g,b,255]
        color_groups[color] = group
    return color_groups

def test(img_num):        
    color_groups = get_color_groups(img_num)
    for color_group in color_groups.values():
        plt.imshow(color_group)
        plt.show()

if __name__ == '__main__':
    # test(636382)
    print(enclosure_strengths([[1, 1, 1], 
                               [1, 0, 2], 
                               [1, 1, 1]], 3))
    print(enclosure_strengths([[1, 1, 1, 1, 1],
                               [1, 0, 0, 0, 1],
                               [1, 0, 2, 0, 1],
                               [1, 0, 0, 0, 1],
                               [1, 1, 1, 1, 1]], 3))
