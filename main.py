"""
Provides simplistic functionality through tkinter GUI to count the number of cells from a CZI (Carl Zeiss) 
given a certain region of interest. 
"""

__author__ = "Ben Kurzion"
__email__ = "benkurzion@gmail.com"
__maintainer__ = "Ben Kurzion"
__status__ = "Prototype"


import tkinter as tk
from tkinter import messagebox
from tkinter.filedialog import askopenfilename
from PIL import Image, ImageTk
import numpy as np
import czifile
import cv2
from skimage import measure
import math
from sklearn.cluster import KMeans
from kneed import KneeLocator
import matplotlib.pyplot as plt
import warnings



def calculateNumCells(channel, boundingBox) -> int:
    x0, y0, x1, y1 = boundingBox
    #cv2.imshow("channel image", channel)
    #cv2.waitKey(0)
    
    #Threshold image to binary using OTSU. All cells = 1 and background = 0
    _, thresh = cv2.threshold(channel, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    #cv2.imshow("thresholded", thresh)
    #cv2.waitKey(0)

    #crop the thresholded image 
    thresh = thresh[y0:y1, x0:x1]
    

    #markers = binary array signaling cell vs background
    _, markers = cv2.connectedComponents(thresh) #thresh
    regions = measure.regionprops(markers, intensity_image=thresh)

    numCells = 0
    for region in regions:
        xVals = []
        sseVals = []
        pixelCoords = region.coords.tolist()
        upperBound = min(15, len(pixelCoords))
        for k in range (1, upperBound):
            model = KMeans(n_clusters=k, random_state=0, n_init=10)
            model.fit(pixelCoords)
            sseVals.append(model.inertia_)
            xVals.append(k)
        """plt.plot(xVals, sseVals)
        plt.xlabel('Number of clusters')
        plt.ylabel('SSE')
        plt.show()"""
        #Find the number of distinct cells using elbow plot of k-means SSE
        if len(xVals) > 0 and len(sseVals) > 0:
            warnings.filterwarnings("ignore")
            numOptimalClusters = KneeLocator(xVals, sseVals, curve='convex', direction='decreasing').knee
            #print("Elbow found at ", numOptimalClusters)
            if numOptimalClusters is not None:
                numCells = numCells + numOptimalClusters
            warnings.resetwarnings()
    return numCells

class BoundingBox:
    def __init__(self):
        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None
        self.started = False

    def start_box(self, event):
        self.started = True
        self.start_x = event.x
        self.start_y = event.y

    def draw_box(self, event):
        if self.started:
            self.end_x = event.x
            self.end_y = event.y
            canvas.create_rectangle(self.start_x, self.start_y, self.end_x, self.end_y, outline="red", tags="bbox")

    def end_box(self, event):
        if self.started:
            self.started = False
            self.end_x = event.x
            self.end_y = event.y
            if self.start_x != self.end_x and self.start_y != self.end_y:
                global croppedImage

                #erase the canvas from the grid
                #canvas.grid_remove()

                #coords for the bounding box
                x0 = min(self.start_x, self.end_x)
                y0 = min(self.start_y, self.end_y)
                x1 = max(self.start_x, self.end_x)
                y1 = max(self.start_y, self.end_y)
                boundingBoxCoords = (x0, y0, x1, y1)

                #crop the image and put it in the GUI
                pilImage = ImageTk.getimage(image)
                croppedImage = pilImage.crop(boundingBoxCoords)
                croppedImage = ImageTk.PhotoImage(image = croppedImage)
                croppedLabel.config(image = croppedImage)

                #count the cells for all other channels
                print("Number of cells from channel 2 = ", calculateNumCells(channel = channel2, boundingBox=boundingBoxCoords))
                print("Number of cells from channel 3 = ", calculateNumCells(channel = channel3, boundingBox=boundingBoxCoords))
                print("Number of cells from channel 4 = ", calculateNumCells(channel = channel4, boundingBox=boundingBoxCoords))
    

def getImage() -> None:
    """
    Opens windows / mac file explorer and saves user provided file path to jpg file
    """

    filePath = askopenfilename()
    if len(filePath) > 3 and filePath[-3:].lower() != "czi":
        messagebox.showerror(title="Fatal Error", message= "Please enter a .czi file and try again")
    elif filePath:
        global image, channel1, channel2, channel3, channel4 #to prevent garbage collection from stealing the image!!
        image = czifile.imread(filePath)
        image = image[0, 0, 0, :, 0, :, :, 0]
        channel1 = image[0,:,:]  #First channel = composite image
        channel2 = image[1,:,:]
        channel3 = image[2,:,:]
        channel4 = image[3,:,:]
        #.astype('uint8')
        image = Image.fromarray(channel1)
        image = image.resize((500,500))  
        image = ImageTk.PhotoImage(image = image)

        canvas.create_image(0, 0, anchor = 'nw', image = image)

        canvas.bind("<Button-1>", bbox.start_box)
        canvas.bind("<B1-Motion>", bbox.draw_box)
        canvas.bind("<ButtonRelease-1>", bbox.end_box)

    else:
        messagebox.showerror(title="Fatal Error", message= "Error. Try Again")

def recalc():
    canvas.delete("all")
    try:
        originalImage = ImageTk.getimage(croppedImage)
        blankImage = Image.new("RGB", originalImage.size, (255, 255, 255))
        blankImage = ImageTk.PhotoImage(blankImage)
        croppedLabel.config(image=blankImage)
    except NameError:
        print("cropped image does not exist yet")


#Runnable

filePath : str = None
root = tk.Tk()
root.geometry("800x600")
root.title("Cell Counter Application")

openImageBtn = tk.Button(root, text ="Upload a czi file", command = getImage, background="black", foreground= "white").grid(row=0, column=0)
exitBtn = tk.Button(root, text ="Restart", command= recalc, background="black", foreground= "white").grid(row=0, column=1)


canvas = tk.Canvas(root, width=500, height=500)
canvas.grid(row=1, column=0)

croppedLabel = tk.Label(root)
croppedLabel.grid(row=1, column=1)

bbox = BoundingBox()

root.mainloop()

