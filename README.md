

# Pupilometry
[![DOI](https://zenodo.org/badge/439247676.svg)](https://zenodo.org/badge/latestdoi/439247676)  
It is commonly hard to take image using CMOS (or CCD) sensor during taking MRI (magnetic resonance imaging) signal due to the magnetic compatibility or electromagnetic interference. For that, we bought commercialized MR compatible camera and have developed this software to control the devices conveniently. This tool implement the keypoint detection model to automatically measure the pupil size in real time. If you want to detect keypoint from another type object, refer this [site][DLC] and train for your data  

[DLC]: https://github.com/DeepLabCut/DeepLabCut

# Requirements
Copy below files from [here](https://github.com/TheImagingSource/IC-Imaging-Control-Samples/tree/master/Python/tisgrabber/samples) and paste to `lib` directory  
```
TIS_UDSHL11_x64.dll   
tisgrabber_x64.dll   
```  
Refer to the [conda envrionment](/environment.yml) file for installing python packages


# Test environment
```
CPU : AMD Ryzen 9 5900X
GPU : NVIDIA GeForceRTX 3080Ti
memory : 64 GB
OS : windows11
Virtual env : Conda
TTL generator : Master9
```

# hardware
We used commercial MR compatible camera(12M-i, MRC), filter box and TTL recevier (Adventech) bought from [MRC](https://www.mrc-systems.de/en/products/mr-compatible-cameras#12m-i-camera).  
I designed this software to recognize the TTL signal that `Vpp=5V`, `Vmax=5V`, `Vmin=0` and `duration > 200ms`

# Run
Run `FlyingSesame.py` file in terminal
```
python FlyingSesame.py
```
![캡처](/movie/sample_movie.gif)

# Mascot
![Sesame](/movie/mascot_sesame.jpg)

# Reference
[1] https://github.com/TheImagingSource/IC-Imaging-Control-Samples
[2] https://github.com/DeepLabCut/DeepLabCut
