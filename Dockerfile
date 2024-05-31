# Pull the Python image from Docker Hub
FROM python:latest

# Image Labels. Update values for each build
LABEL Name="Skill-Forge"
LABEL Version=1.3.2
LABEL Release="pre-release"
LABEL ReleaseDate="18-05-2024"
LABEL Description="Skill Forge is a open-source platform for learning and practicing programming languages."
LABEL Maintainer="Aleksandar Karastoyanov <karastoqnov.alexadar@gmail.com>"
LABEL License="GNU GPL v3.0 license"
LABEL GitHub SourceCode="https://github.com/SoftUni-Discord-Community/skill_forge"


# Set the environment variable for the timezone
ENV TZ=Europe/Sofia

# Install tzdata for timezone setting
RUN apt-get update && \
    apt-get install -y tzdata && \
    ln -fs /usr/share/zoneinfo/$TZ /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata


# Set the working directory in the container
WORKDIR /app

# Copy the Python app requirements file into the container at /app
COPY ./requirements.txt /app/requirements.txt

# Install the Python app requirements
RUN pip install -r requirements.txt --no-cache

# Install NodeJS interpreter, Mono runtime and OpenJDK 17 compilers
RUN apt update && apt install nodejs npm mono-complete openjdk-17-jdk-headless -y

# Copy the current directory contents into the container at /app
COPY . /app

# Install the node modules
RUN npm install

# Buld the dependencies
RUN npm run build

# Expose port 5000
EXPOSE 5000

# Configure the container to run as an executable
ENTRYPOINT ["python"]

# Run the Python app
CMD ["run.py"]