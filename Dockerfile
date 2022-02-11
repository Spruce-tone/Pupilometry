FROM ubuntu:20.04
RUN apt-get -y update
RUN apt-get -y install python3.8
RUN apt-get -y install python3-pip
# These commands install the cv2 dependencies that are normally present on the local machine, but might be missing in your Docker container causing the issue.
RUN apt-get install ffmpeg libsm6 libxext6  -y
RUN pip3 install numpy opencv-python scikit-image PyQt5 pyinstaller tensorflow-gpu==2.7
