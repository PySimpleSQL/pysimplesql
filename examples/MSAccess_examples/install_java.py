"""
OpenJDK Java Temporary/Local installation to support MS Access examples.

The current implementation of the MSAccess SQLDriver uses the JPype library to interface
with the UCanAccess java JDBC driver, which requires Java to be installed in order to
run.  This also serves as an example to automatically download a local Java installation
for your own projects.
"""
import configparser
import os
import pathlib
import pysimplesql as ss
import PySimpleGUI as sg
import subprocess

try:
    import jdk
except ModuleNotFoundError:
    sg.popup_error("You must `pip install install-jdk` to use this example")
    exit(0)

SETTINGS_FILE = pathlib.Path.cwd() / "settings.ini"


# -------------------------------------------------
# ROUTINES TO INSTALL JAVA IF USER DOES NOT HAVE IT
# -------------------------------------------------
def _is_java_installed() -> bool:
    if "JAVA_HOME" in os.environ:
        return True
    previous_jre = load_setting("General", "java_home")
    if previous_jre:
        os.environ["JAVA_HOME"] = previous_jre
        return True
    # Returns True if Java is installed, False otherwise
    try:
        subprocess.check_output(["which", "java"])
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def java_install(version: str = "11", jre: bool = True):
    return jdk.install(version, jre=jre)


def java_check_install() -> bool:
    """
    Checks to see if Java is installed. If it is not installed, then a local
    installation process can start automatically with user permission.

    :returns: True if it is ok to proceed after this call, False otherwise
    """
    if not _is_java_installed():
        res = sg.popup_yes_no(
            "Java is required but not installed.  Would you like to install it?",
            title="Java not found",
        )
        if res == "Yes":
            config = {
                "phrases": [
                    "Please wait while OpenJDK JRE is installed locally...",
                    "Still working... Thank you for your patience.",
                ]
            }
            pa = ss.ProgressAnimate("Installing Java Open-JDK JRE", config)
            # Update the default phrases shown in the ProgressAnimation

            try:
                java_home = pa.run(java_install)
            except Exception as e:  # noqa: BLE001
                print(e)
                sg.popup(f"There was an error installing Java: {e}")
                pa.close()
                return False
            pa.close()
            # Set JAVA_HOME and save it to settings
            os.environ["JAVA_HOME"] = java_home
            save_setting("General", "java_home", java_home)
        else:
            url = jdk.get_download_url(11, jre=True)
            sg.popup(
                f"Java is required to run this example.  You can download it at: {url}"
            )
            return False

    if not os.environ.get("JAVA_HOME"):
        sg.popup("'JAVA_HOME' must be set in order to run this example")
        return False

    return True


def save_setting(section: str, key: str, value: str) -> None:
    config = configparser.ConfigParser()
    config.read(SETTINGS_FILE)

    # Create the section if it doesn't exist
    if section not in config:
        config[section] = {}

    # Set the value in the section
    config[section][key] = value

    # Save the settings to the file
    with open(SETTINGS_FILE, "w") as config_file:
        config.write(config_file)


def load_setting(section: str, key: str, default=None) -> str:
    config = configparser.ConfigParser()
    config.read(SETTINGS_FILE)

    # Check if the section and key exist
    if section in config and key in config[section]:
        return config[section][key]

    return default


if __name__ == "__main__":
    if java_check_install():
        print("Java is installed.")
    else:
        print("Java is not installed.")
    exit(0)
