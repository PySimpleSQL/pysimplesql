"""
CREATE A DOCKER IMAGE AND PUBLISH IT TO DOCKER HUB

Note: This is not used by the end user!
This file is used to create/update the docker image used to provide a Postgres image
pre-populated with Tables used for pysimplesql examples.
"""
import docker
import time
from getpass import getpass
from tqdm import tqdm

# Set up the Docker client
client = docker.from_env()

# Prompt for Docker Hub login credentials
username = input("Enter Docker Hub username: ")
password = getpass("Enter Docker Hub password: ")

# Authenticate with Docker Hub
client.login(username=username, password=password)

# Build the Docker image from the Dockerfile
print("Building Docker image...")
with tqdm(total=1, desc="Building Docker image") as pbar:
    image, build_logs = client.images.build(
        path=".", dockerfile="Dockerfile2", tag="pysimplesql/examples:postgres"
    )
    pbar.update()

# Start a new container based on the new image
print("Starting container...")
with tqdm(total=1, desc="Starting container") as pbar:
    container = client.containers.run(
        image, name="pysimplesql-postgres", detach=True, ports={"5432/tcp": 5432}
    )
    pbar.update()

# Print the container logs
print(container.status)

# Wait for the container to start up
print("Waiting for container to start up...")
time.sleep(5)
with tqdm(desc="Starting up container") as pbar:
    container.reload()
    while True:
        if "Status" in container.attrs["State"]:
            if container.attrs["State"]["Status"] == "running":
                break
        time.sleep(1)
        pbar.update()

print("Waiting for database population...")
time.sleep(30)

# Commit the container to a new image
print("Committing container to a new image...")
with tqdm(total=1, desc="Committing container") as pbar:
    image = container.commit(repository="pysimplesql/examples", tag="postgres")
    pbar.update()

# Stop and remove the container
print("Stopping and removing container...")
with tqdm(total=1, desc="Stopping container") as pbar:
    container.stop()
    container.remove()
    pbar.update()


# Push the new image to Docker Hub
print("Pushing image to Docker Hub...")
with tqdm(total=1, desc="Pushing image to Docker Hub") as pbar:
    client.images.push("pysimplesql/examples", "postgres")
    pbar.update()

# Clean up
print("Cleaning up...")
with tqdm(total=1, desc="Cleaning up") as pbar:
    client.images.remove(image.id)
    pbar.update()

print("Done!")
