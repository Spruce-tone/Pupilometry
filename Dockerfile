# FROM ubuntu:20.04
# RUN apt-get -y update 
# RUN apt-get -y install python3.7 
# RUN apt-get -y install python3-pip
#     # These commands install the cv2 dependencies that are normally present on the local machine, but might be missing in your Docker container causing the issue.
# RUN apt-get install ffmpeg libsm6 libxext6  -y
# RUN pip3 install "deeplabcut[gui]>=2.2.0.2" deeplabcut-live numpy==1.19.5 decorator==4.4.2 tensorflow==2.5.0 PyQt5 scikit-image pyqtgraph  opencv-python 

# FROM deeplabcut/deeplabcut:base

# RUN DEBIAN_FRONTEND=noninteractive apt-get update -yy \ 
#     && DEBIAN_FRONTEND=noninteractive \
#          apt-get install -yy --no-install-recommends \
#          libgtk-3-dev python3-wxgtk4.0 locales \
#     && apt-get clean \
#     && rm -rf /var/lib/apt/lists/* \
#     && locale-gen en_US.UTF-8 en_GB.UTF-8

# RUN pip install --no-cache-dir --upgrade pip \
#  && pip install --no-cache-dir --upgrade "deeplabcut[gui]>=2.2.0.2" deeplabcut-live numpy==1.19.5 decorator==4.4.2 tensorflow==2.5.0 PyQt5 scikit-image pyqtgraph  opencv-python 

# ENV DLClight=False
# # CMD ["cd", "data"]
# # CMD ["python3", "-m", "FlyingSesame.py"]

# -------------
FROM continuumio/miniconda3:latest

RUN apt-get update -y; apt-get upgrade -y
RUN apt-get update -y; apt-get upgrade -y; apt-get install -y vim-tiny vim-athena ssh

COPY environment.yml environment.yml

RUN conda env create -f environment.yml
RUN echo "alias l='ls -lah'" >> ~/.bashrc
RUN echo "source activate coin" >> ~/.bashrc

ENV CONDA_EXE /opt/conda/bin/conda
ENV CONDA_PREFIX /opt/conda/envs/livepupil4
ENV CONDA_PYTHON_EXE /opt/conda/bin/python
ENV CONDA_PROMPT_MODIFIER (livepupil4)
ENV CONDA_DEFAULT_ENV livepupil4
ENV PATH /opt/conda/envs/livepupil4/bin:/opt/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
