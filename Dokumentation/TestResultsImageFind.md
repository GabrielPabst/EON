Test Results OpenCV Template Matching | SIFT | SURF

```
1. Template 2.SIFT 3. SURF
LARGER IMAGE WITH SLIGHT DIFFERENCE

PS C:\Users\gabri\Desktop\Schule\Diplomarbeit\EON\Tests\ImageTest> python.exe .\main.py .\assets\icon.jpg .\assets\screenshot.jpg image
Best match found at (x=799, y=471)
Match confidence: 0.89
Processing time: 0.889 seconds
Result saved to result.jpg

PS C:\Users\gabri\Desktop\Schule\Diplomarbeit\EON\Tests\ImageTest> python.exe .\main.py .\assets\icon.jpg .\assets\screenshot.jpg sift 
Best match found at (x=796, y=466)
Match confidence: 0.36
Processing time: 0.583 seconds
Result saved to result.jpg

PS C:\Users\gabri\Desktop\Schule\Diplomarbeit\EON\Tests\ImageTest> python.exe .\main.py .\assets\icon.jpg .\assets\screenshot.jpg surf
Best match found at (x=796, y=466)
Match confidence: 0.36
Processing time: 0.552 seconds
Result saved to result.jpg


SMALLER IMAGE / ICON 

PS C:\Users\gabri\Desktop\Schule\Diplomarbeit\EON\Tests\ImageTest> python.exe .\main.py .\assets\icon2.jpg .\assets\screenshot.jpg image 
Best match found at (x=3, y=108)
Match confidence: 0.94
Processing time: 0.866 seconds
Result saved to result.jpg

PS C:\Users\gabri\Desktop\Schule\Diplomarbeit\EON\Tests\ImageTest> python.exe .\main.py .\assets\icon2.jpg .\assets\screenshot.jpg sift  
Best match found at (x=-2, y=102)
Match confidence: 0.55
Processing time: 0.634 seconds
Result saved to result.jpg

PS C:\Users\gabri\Desktop\Schule\Diplomarbeit\EON\Tests\ImageTest> python.exe .\main.py .\assets\icon2.jpg .\assets\screenshot.jpg surf
Best match found at (x=-2, y=102)
Match confidence: 0.55
Processing time: 0.581 seconds
Result saved to result.jpg


ONLY TEXT DIFFERENCE OTHER SIMMILAR

PS C:\Users\gabri\Desktop\Schule\Diplomarbeit\EON\Tests\ImageTest> python.exe .\main.py .\assets\icon3.jpg .\assets\screenshot2.jpg image
Best match found at (x=631, y=753)
Match confidence: 0.99
Processing time: 1.372 seconds
Result saved to result.jpg

PS C:\Users\gabri\Desktop\Schule\Diplomarbeit\EON\Tests\ImageTest> python.exe .\main.py .\assets\icon3.jpg .\assets\screenshot2.jpg sift 
Best match found at (x=616, y=751)
Match confidence: 0.16
Processing time: 0.773 seconds
Result saved to result.jpg

PS C:\Users\gabri\Desktop\Schule\Diplomarbeit\EON\Tests\ImageTest> python.exe .\main.py .\assets\icon3.jpg .\assets\screenshot2.jpg surf
Best match found at (x=616, y=751)
Match confidence: 0.16
Processing time: 0.621 seconds
Result saved to result.jpg



ALTERNATIVE ORB RULED OUT: 
PS C:\Users\gabri\Desktop\Schule\Diplomarbeit\EON\Tests\ImageTest> python.exe .\main.py .\assets\icon3.jpg .\assets\screenshot2.jpg orb 
No match found.
PS C:\Users\gabri\Desktop\Schule\Diplomarbeit\EON\Tests\ImageTest> python.exe .\main.py .\assets\icon2.jpg .\assets\screenshot.jpg orb 
No match found.
PS C:\Users\gabri\Desktop\Schule\Diplomarbeit\EON\Tests\ImageTest> python.exe .\main.py .\assets\icon.jpg .\assets\screenshot.jpg orb    
Best match found at (x=1644, y=76)
Match confidence: 0.37
Processing time: 0.439 seconds
Result saved to result.jpg => WRONG RESULTS
```
