"""
DOCKER UTILITIES

This file is not used for pysimplesql base installation. It exists only as a collection
of utility functions for examples which provide databases in Docker containers for
testing purposes.
"""
import logging
import time

import docker

from pysimplesql import ProgressBar

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
    image: str, container_name: str, ports: dict
) -> docker.models.containers.Container:
    """
    Create and/or start a Docker container with the specified image and container name.

    :param image: The Docker image to use for the container
    :param container_name: The name to use for the container
    :param ports: The ports to pass to the Docker container. Example:
        {"5432/tcp": ("127.0.0.1", 5432)}
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
            ports=ports,
            detach=True,
            auto_remove=True,
        )
        # time.sleep(1)

    # Now we can start the container
    logger.info(f"Starting container {container_name}...")
    container = client.containers.get(container_name)
    logger.info(f"container_status: {container.status}")
    if container.status != "running":
        logger.info("STARTING CONTAINER")
        container.start()

    # Wait for the container to be fully initialized
    retries = 3
    progress_bar = ProgressBar(
        title="Waiting for container to start", max_value=retries, hide_delay=1000
    )
    for progress in range(retries):
        container.reload()
        if container.status == "running":
            logs = container.logs().decode("utf-8")
            # TODO: Refactor to include callback or other mechanism to determine if
            # a container is fully initialized, since this needs to be more general
            # purpose. For now, this should work in both Postgres and MySQL
            if "ready" in logs and "connect" in logs:
                progress_bar.close()
                return container
        progress_bar.update("Container initializing...", progress)
        time.sleep(1)

    return None
