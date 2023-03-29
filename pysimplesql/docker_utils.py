"""
DOCKER UTILITIES 

This file is not used for pysimplesql base installation. It exists only as a collection
of utility functions for examples which provide databases in Docker containers for 
testing purposes.
"""
import docker
from pysimplesql import ProgressBar
import time
import logging

# Set the logging level here (NOTSET,DEBUG,INFO,WARNING,ERROR,CRITICAL)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def docker_image_installed(image: str) -> bool:
    """
    Check if the specified Docker image is installed locally.

    :param image: The Docker image, including the tag ("pysimplesql/examples:postgres")
    :return: True if the image is installed, False otherwise
    """
    client = docker.from_env()
    try:
        client.images.get(image)
        return True

    # This isn't a great solution, but ss will not require docker this way
    except:  # noqa: E722
        return False


def docker_image_is_latest(image: str) -> bool:
    """
    Check if a new version of a Docker image is available for download.

    :param image: The Docker image, including the tag ("pysimplesql/examples:postgres")
    :return: True if a newer version is available, False otherwise
    """
    client = docker.from_env()

    # Split the image name and tag
    image_name, image_tag = image.split(":")

    # Get the installed image and the latest available image
    installed_image = client.images.get(image)
    latest_image = client.images.get(f"{image_name}:{image_tag}")

    # Compare the IDs of the installed and latest images
    return installed_image.id == latest_image.id


def docker_image_pull(image: str, latest: bool = True) -> None:
    """
    Pull the supplied docker image, displaying a progress bar.

    :param latest: Ensure that the latest docker image is used (updates the local image)
    :return:
    """
    client = docker.from_env()
    # Check if the installed image is installed, and if it is the latest.
    # Also check to see if the latest was requested in the function call
    if docker_image_installed(image):
        if docker_image_is_latest(image):
            return
        if not latest:
            return

    # Pull the Docker image and stream the output to the progress bar
    started = False  # Has the first download started?
    layers = 0  # Number of fs layers to download
    progress = 0  # The progress, against the number of layers to download

    for line in client.api.pull(image, stream=True, decode=True):
        if "status" in line:
            if line["status"] == "Pulling fs layer":
                # count the layers we will be downloading
                layers += 1
            elif line["status"] == "Downloading" and not started:
                # We have started the first download.  We should now have an accurate
                # count of the number of fs layers for progress update.
                # Create a progress bar with a maximum value of the number of layers
                started = True
                progress_bar = ProgressBar(
                    title="Pulling Docker image", max_value=layers
                )
                progress_bar.update("waiting on downloads to start.", progress)
            elif line["status"] == "Pull complete":
                progress += 1
                message = f"Puling {image}\n{progress} of {layers} layers complete."
                progress_bar.update(message=message, current_count=progress)
        elif "error" in line:
            raise Exception(line["error"])
    # Close the progress bar
    progress_bar.close()


def docker_container_start(
    image: str, container_name: str
) -> docker.models.containers.Container:
    """
    Create and/or start a Docker container with the specified image and container name.

    :param image: The Docker image to use for the container
    :param container_name: The name to use for the container
    :return: The Docker container object
    """
    client = docker.from_env()

    # Check if the container already exists
    existing_containers = client.containers.list(
        all=True, filters={"name": container_name}
    )

    if not existing_containers:
        # If the container doesn't exist, create it
        logger.info(f"The {container_name} container does not exist. Creating...")
        client.containers.create(
            image=image,
            name=container_name,
            ports={"5432/tcp": ("127.0.0.1", 5432)},
            detach=True,
            auto_remove=True,
        )

    # Now we can start the container
    logger.info(f"Starting container {container_name}...")
    container = client.containers.get(container_name)
    logger.info(f"container_status: {container.status}")
    if container.status != "running":
        logger.info("STARTING CONTAINER")
        steps = 2
        progress_bar = ProgressBar(title="Starting Docker container", max_value=steps)
        container.start()

        for i in range(steps):
            progress_bar.update("Container starting...", i)
            time.sleep(1)
        progress_bar.close()

    # Wait for the container to be fully initialized
    while True:
        container.reload()
        if container.status == "running":
            logs = container.logs().decode("utf-8")
            if "database system is ready to accept connections" in logs:
                logger.info("Ready to connect!")
                break
        time.sleep(1)

    return container
