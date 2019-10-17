FROM continuumio/miniconda3:latest

# create root directory for our project in the container
RUN mkdir /ErrorLogClustering
# Set the working directory to /ErrorLogClustering
WORKDIR /ErrorLogClustering
# Copy the current directory contents into the container at /ErrorLogClustering
ADD . /ErrorLogClustering/

# Install any needed packages specified in environment.yml
COPY environment.yml ./
RUN conda env create -f environment.yml
RUN echo "source activate $(head -1 environment.yml | cut -d' ' -f2)" > ~/.bashrc
ENV PATH /opt/conda/envs/$(head -1 environment.yml | cut -d' ' -f2)/bin:$PATH